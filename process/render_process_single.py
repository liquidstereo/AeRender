#!/usr/bin/env python3

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
import threading
import glob
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, List, Tuple, Optional
from alive_progress import alive_bar

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from configs import Msg, DEFAULT_TEMP_DIR, DEFAULT_OUTPUT_DIR

from scripts import (
    get_rel_path, get_short_path, setup_handler, is_shutdown_requested, process_kill,
    make_dir, trace_error, get_usable_workers,
    activate_system_monitor, sanitize_names, format_elapsed_time
)
from scripts._sig_handler import reset_shutdown_event
from scripts._ae_specifics import load_json_data

from .render_logger import render_info_log, render_result_log

def setup_workspace(recipe: Dict[str, Any], logger) -> bool:
    try:
        project_settings = recipe['project_settings']
        source_project = project_settings['project_file']
        temp_project = project_settings.get('temp_project',
                                           os.path.join(project_settings['temp_directory'],
                                                       f"temp_{os.path.basename(source_project)}"))

        logger.info(f"Checking source project: {source_project}")

        if not os.path.exists(source_project):
            logger.error(f"Source project not found: {source_project}")
            return False

        temp_dir = os.path.dirname(temp_project)
        if not make_dir(temp_dir):
            logger.error(f"Failed to create temp directory: {temp_dir}")
            return False

        shutil.copy2(source_project, temp_project)
        logger.info(f"Project file copied: {temp_project}")

        for comp_name, comp_data in recipe['result_outputs'].items():
            if 'workflow' in comp_data and 'chunk_tasks' in comp_data['workflow']:
                for task in comp_data['workflow']['chunk_tasks']:
                    chunk_dir = task['temp_directory']
                    if not make_dir(chunk_dir):
                        logger.warning(f"Failed to create chunk directory: {chunk_dir}")

        return True

    except Exception as e:
        logger.error(f"Workspace setup failed: {trace_error(e)}")
        return False

def monitor_progress_files(temp_workspace: str, comp_name: str, file_ext: str,
                         bar, monitor_stop_event: threading.Event, total_frames: int,
                         progress_index: str, total_index: str, result_dirs, logger,
                         completion_flag: threading.Event):

    last_count = 0
    title_changed = False

    try:
        sanitized_comp = sanitize_names(comp_name, strict=True)

        while not monitor_stop_event.is_set() and not is_shutdown_requested():
            patterns = [
                os.path.join(temp_workspace, f'tmp_{sanitized_comp}*', f'*.{file_ext}'),
                os.path.join(temp_workspace, f'tmp_{sanitized_comp}*', f'{sanitized_comp}.*'),
            ]

            all_files = []
            for pattern in patterns:
                files = glob.glob(pattern)
                all_files.extend(files)

            all_files_set = set(all_files)
            current_count = len(all_files_set)

            if current_count > last_count:
                if not title_changed and current_count > 0:
                    bar.title = f'Render In Progress… [{progress_index}/{total_index}]'.upper()
                    title_changed = True

                for _ in range(current_count - last_count):
                    bar()
                last_count = current_count

            if last_count >= total_frames:
                if completion_flag:
                    completion_flag.set()

                bar.title = f'Render Completed…   [{progress_index}/{total_index}]'.upper()
                comp_idx = int(progress_index) - 1
                result_dir = get_short_path(result_dirs[comp_idx], base_dir=DEFAULT_OUTPUT_DIR)
                result_msg = (
                        f'Render For "{comp_name}" Completed. '
                        f'(Result: {result_dir}, '
                        f'{total_frames} Files)'
                    )
                bar_text = Msg.Dim(result_msg, verbose=True)
                bar.text = bar_text

                monitor_stop_event.set()
                break

            time.sleep(0.1)

    except Exception:
        pass

def execute_aerender_command(aerender_cmd: List[str], task_id: int, expected_files: int = 0) -> Dict[str, Any]:
    start_time = time.time()

    try:
        result = subprocess.run(
            aerender_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'
        )

        end_time = time.time()
        elapsed = end_time - start_time

        return {
            'task_id': task_id,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'elapsed': elapsed,
            'files_rendered': expected_files if result.returncode == 0 else 0,
            'success': result.returncode == 0,
            'command': ' '.join(aerender_cmd)
        }

    except subprocess.TimeoutExpired:
        return {
            'task_id': task_id,
            'exit_code': -1,
            'stdout': '',
            'stderr': 'Command timed out after 300 seconds',
            'elapsed': 300,
            'files_rendered': 0,
            'success': False,
            'command': ' '.join(aerender_cmd)
        }
    except Exception as e:
        return {
            'task_id': task_id,
            'exit_code': -1,
            'stdout': '',
            'stderr': str(e),
            'elapsed': time.time() - start_time,
            'files_rendered': 0,
            'success': False,
            'command': ' '.join(aerender_cmd)
        }

def run_render_tasks_parallel(tasks: List[Dict[str, Any]], workers: int, logger, render_stop_event,
                    bar=None, progress_index=None, total_index=None) -> List[Dict[str, Any]]:
    results = []

    if not tasks:
        logger.warning('No tasks to execute')
        return results

    logger.info(f'Starting multiprocessing: {len(tasks)} tasks, {workers} workers')
    logger.debug(f'Task details: {[task.get("task_detail", task.get("comp_name", "unknown")) for task in tasks]}')

    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = []

            for i, task in enumerate(tasks):
                if is_shutdown_requested():
                    logger.warning(f'User shutdown requested during task submission at {i+1}/{len(tasks)}')
                    break

                aerender_cmd = task['aerender_command']
                expected_files = task.get('expected_files', 0)
                future = executor.submit(execute_aerender_command, aerender_cmd, i + 1, expected_files)
                futures.append((future, task))

            if not futures:
                logger.warning('No tasks were submitted for processing')
                return results

            logger.info(f'Submitted {len(futures)} tasks for processing')

            total_files_rendered = 0
            total_errors = 0

            for i, (future, task_info) in enumerate(futures):
                if is_shutdown_requested():
                    logger.warning(f'User shutdown requested, forcing task completion {i+1}/{len(futures)}')
                    for j, (remaining_future, remaining_task) in enumerate(futures[i:], i):
                        try:
                            result = remaining_future.result(timeout=120)
                            remaining_future._cached_result = result
                        except Exception as timeout_e:
                            logger.error(f'Forced completion failed for task {j+1}: {timeout_e}')
                    break

                try:
                    if hasattr(future, '_cached_result'):
                        result = future._cached_result
                    else:
                        result = future.result(timeout=600)

                    files_rendered = result.get('files_rendered', 0)
                    total_files_rendered += files_rendered

                    if result.get('success', False):
                        elapsed_str = format_elapsed_time(result.get('elapsed', 0))
                        task_detail = task_info.get('task_detail', f'Task {i+1}')

                        logger.info(f'Task {i+1}/{len(futures)} success ({task_detail}: files: {files_rendered}, elapsed: {elapsed_str})')
                    else:
                        total_errors += 1
                        task_detail = task_info.get('task_detail', f'Task {i+1}')
                        logger.error(f'Task {i+1}/{len(futures)} failed ({task_detail}): {result.get("stderr", "Unknown error")}')

                    task_result = {
                        'task_id': result.get('task_id', i + 1),
                        'task_detail': task_info.get('task_detail', f'Task {i+1}'),
                        'files_rendered': files_rendered,
                        'elapsed': result.get('elapsed', 0),
                        'success': result.get('success', False),
                        'exit_code': result.get('exit_code', -1)
                    }
                    results.append(task_result)

                except Exception as e:
                    total_errors += 1
                    error_msg = trace_error(e)
                    task_detail = task_info.get('task_detail', f'Task {i+1}')
                    logger.error(f'Task {i+1}/{len(futures)} failed ({task_detail}): {error_msg}')

            logger.info(f'All tasks completed: {len(tasks)} tasks, {total_files_rendered} files rendered, {len(results)-total_errors} success, {total_errors} errors')

    except KeyboardInterrupt:
        logger.warning('Rendering interrupted by user (Ctrl+C)')
        raise
    except Exception as e:
        logger.error(f'Critical error in multiprocessing execution: {trace_error(e)}')
        raise

    return results

def update_status(recipe: Dict[str, Any], json_path: str, logger) -> bool:
    try:
        for comp_name, comp_data in recipe['result_outputs'].items():
            if 'frames' in comp_data:
                for frame_num, frame_info in comp_data['frames'].items():
                    tmp_path = frame_info.get('tmp', '')
                    if tmp_path and os.path.exists(tmp_path):
                        frame_info['rendered'] = True

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(recipe, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON status updated: {json_path}")
        return True

    except Exception as e:
        logger.error(f"JSON status update failed: {trace_error(e)}")
        return False

def execute_render(json_path: str, enable_logs: bool = False, preview: bool = False) -> Tuple[int, str]:
    try:
        recipe = load_json_data(json_path)

        from .render_logger import get_logger
        logger = get_logger()

        render_info_log(recipe, enable_logs, preview, logger)
        logger.info('Execution mode: Single composition optimized parallel execution')

        temp_dir = recipe['project_settings']['temp_directory']
        setup_handler(logger, temp_dir)

        if not setup_workspace(recipe, logger):
            Msg.Error("Workspace setup failed")
            return 1, ""

        workers = recipe['worker_configuration']['configured_workers']
        comp_names = list(recipe['result_outputs'].keys())
        total_comps = len(comp_names)
        all_results = []

        for comp_index, comp_name in enumerate(comp_names, 1):
            reset_shutdown_event()

            comp_data = recipe['result_outputs'][comp_name]
            comp_tasks = []

            if 'workflow' in comp_data and 'chunk_tasks' in comp_data['workflow']:
                for task_idx, task in enumerate(comp_data['workflow']['chunk_tasks']):
                    aerender_cmd = task['aerender_command']
                    start_frame = 'N/A'
                    end_frame = 'N/A'

                    try:
                        s_idx = aerender_cmd.index('-s')
                        if s_idx + 1 < len(aerender_cmd):
                            start_frame = aerender_cmd[s_idx + 1]

                        e_idx = aerender_cmd.index('-e')
                        if e_idx + 1 < len(aerender_cmd):
                            end_frame = aerender_cmd[e_idx + 1]
                    except (ValueError, IndexError):
                        chunk_id = task.get('chunk_id', '')
                        if '_' in chunk_id:
                            parts = chunk_id.split('_')
                            if len(parts) >= 3:
                                try:
                                    start_frame = int(parts[-2])
                                    end_frame = int(parts[-1])
                                except ValueError:
                                    pass

                    task['task_detail'] = f'RenderTask_{task_idx+1:02d}'
                    task['expected_files'] = task.get('file_count', 0)
                    comp_tasks.append(task)

            if not comp_tasks:
                logger.warning(f'No tasks found for composition: {comp_name}')
                continue

            total_frames = len(comp_data.get('frames', {}))

            with alive_bar(
                total_frames, spinner=None, title='PLEASE WAIT…', title_length=27,
                length=20, dual_line=True, stats=True, elapsed=True, manual=False,
                enrich_print=False, force_tty=True, refresh_secs=0.1,
                receipt_text=True, monitor_end=True
            ) as bar:
                progress_index = f'{comp_index:02d}'
                total_index = f'{total_comps:02d}'

                bar.title = 'INITIALIZING… PLEASE WAIT… '
                bar_text = Msg.Dim(f'[{progress_index}/{total_index}] '
                                  f'INITIALIZING RENDER EXECUTION. PLEASE WAIT… ', verbose=True)
                bar.text = bar_text

                monitor_stop_event = threading.Event()
                completion_flag = threading.Event()
                render_stop_event = None

                activate_system_monitor(bar, monitor_stop_event, completion_flag)

                temp_workspace = recipe['project_settings']['temp_directory']
                file_ext = recipe['project_settings']['file_extension']
                result_dirs = recipe['project_settings']['result_dir']

                progress_thread = threading.Thread(
                    target=monitor_progress_files,
                    args=(temp_workspace, comp_name, file_ext, bar, monitor_stop_event, total_frames, progress_index, total_index, result_dirs, logger, completion_flag),
                    daemon=True
                )
                progress_thread.start()

                time.sleep(0.5)

                comp_start_time = datetime.now()

                comp_results = run_render_tasks_parallel(comp_tasks, workers, logger, render_stop_event, bar, progress_index, total_index)
                all_results.extend(comp_results)

                comp_end_time = datetime.now()

                completion_flag.set()

                time.sleep(0.5)

                comp_elapsed = comp_end_time - comp_start_time
                comp_elapsed_str = format_elapsed_time(comp_elapsed.total_seconds())
                logger.info(f'Composition completed: {comp_name} ({len(comp_results)} tasks, completed=100%, elapsed: {comp_elapsed_str})')
                logger.debug(f'JSON updated: {comp_name} completion status')

                if comp_name in recipe['result_outputs']:
                    recipe['result_outputs'][comp_name]['elapsed_time'] = comp_elapsed_str

            if comp_index < total_comps:
                print('-')
                time.sleep(1.0)

        if not is_shutdown_requested():
            msg = f'Rendering completed: {len(all_results)} tasks'
            update_status(recipe, json_path, logger)
            logger.info(msg)
        else:
            err_msg = 'Rendering interrupted by user.'
            logger.error(err_msg)
            Msg.Error(err_msg)

        temp_dir = recipe['project_settings']['temp_directory']
        return 0, temp_dir

    except KeyboardInterrupt:
        err_msg = 'Rendering interrupted by user (Ctrl+C).'
        logger.error(err_msg)
        Msg.Error(err_msg)
        return 1, ""

    except Exception as e:
        err_msg = f'Execute render failed: {trace_error(e)}'
        logger.error(err_msg)
        Msg.Error(err_msg)
        return 1, ""

def main():
    parser = argparse.ArgumentParser(description='AeRender v2.0 단일 컴포지션 병렬 렌더링 실행기')
    parser.add_argument('json_path', help='JSON 레시피 파일 경로')
    parser.add_argument('-l', '--logs', action='store_true', help='로그 파일 생성')

    args = parser.parse_args()

    try:
        if not os.path.exists(args.json_path):
            Msg.Error(f'JSON file not found: {args.json_path}')
            return 1

        try:
            recipe = load_json_data(args.json_path)
            if recipe:
                from .render_logger import logger_init

                class TempArgs:
                    def __init__(self, recipe_data):
                        self.logs = args.logs
                        self.fpath = recipe_data['project_settings']['project_file']
                        comp_names = list(recipe_data['result_outputs'].keys())
                        self.comp_name = comp_names[0] if len(comp_names) == 1 else comp_names

                temp_args = TempArgs(recipe)
                logger = logger_init(temp_args, recipe, clear_existing=True)

                Msg.Info('Standalone execution: Logger initialized')

        except Exception as e:
            Msg.Warning(f'Logger initialization failed: {e}')

        exit_code, temp_dir = execute_render(args.json_path, args.logs)

        if exit_code == 0:
            Msg.Info('Rendering execution completed successfully')
        else:
            Msg.Error('Rendering execution failed')

        return exit_code

    except Exception as e:
        Msg.Error(f'Standalone execution failed: {trace_error(e)}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
