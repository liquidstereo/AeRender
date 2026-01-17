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
    get_rel_path, setup_handler, is_shutdown_requested, process_kill,
    make_dir, trace_error, get_usable_workers,
    activate_system_monitor, sanitize_names, format_elapsed_time
)
from scripts._sig_handler import reset_shutdown_event
from scripts._ae_specifics import load_json_data

from .render_logger import render_info_log, render_result_log

def _process_completed_future(future, task_info: Dict[str, Any], completed: int, total: int, results: List, logger, total_files_rendered: int, total_errors: int) -> tuple:
    try:
        if hasattr(future, '_cached_result'):
            result = future._cached_result
        else:
            result = future.result(timeout=0.1)
        results.append(result)

        if isinstance(result, dict):
            files_rendered = result.get('files_rendered', 0)
            execution_time = result.get('execution_time', 0.0)
            error_occurred = not result.get('success', False)

            elapsed_str = format_elapsed_time(execution_time)

            task_detail = task_info.get('task_detail', task_info.get('comp_name', f'Task {completed}'))
            status = "success" if not error_occurred else "failed"
            logger.info(f"Task {completed}/{total} {status} "
                      f"({task_detail}: files: {files_rendered}, elapsed: {elapsed_str})")

            return files_rendered, error_occurred
        else:
            logger.info(f"Task {completed}/{total} completed")
            return 0, False

    except Exception as e:
        task_detail = task_info.get('task_detail', task_info.get('comp_name', f'Task {completed}'))
        err_result = {
            'success': False,
            'task_id': completed,
            'error_msg': trace_error(e),
            'files_rendered': 0,
            'execution_time': 0.0
        }
        results.append(err_result)
        logger.error(f"Task {completed} failed ({task_detail}): {trace_error(e)}")
        return 0, True

def execute_aerender_command(aerender_cmd: List[str], task_id: int, expected_files: int = 0) -> Dict[str, Any]:
    try:
        start_time = datetime.now()

        result = subprocess.run(aerender_cmd, capture_output=True, text=True, timeout=300)

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        files_rendered = expected_files if result.returncode == 0 else 0

        if result.returncode == 0:
            return {
                'success': True,
                'task_id': task_id,
                'error_msg': None,
                'files_rendered': files_rendered,
                'execution_time': execution_time
            }
        else:
            return {
                'success': False,
                'task_id': task_id,
                'error_msg': result.stderr.strip() if result.stderr else 'Unknown error',
                'files_rendered': files_rendered,
                'execution_time': execution_time
            }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'task_id': task_id,
            'error_msg': 'Timeout after 300 seconds',
            'files_rendered': 0,
            'execution_time': 300.0
        }
    except Exception as e:
        try:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
        except:
            execution_time = 0.0

        return {
            'success': False,
            'task_id': task_id,
            'error_msg': str(e),
            'files_rendered': 0,
            'execution_time': execution_time
        }

def setup_workspace(recipe: Dict[str, Any], logger) -> bool:
    try:
        temp_dir = os.path.normpath(recipe['project_settings']['temp_directory'])
        if not make_dir(temp_dir):
            logger.error(f"Failed to create temp directory: {temp_dir}")
            return False

        source_project = os.path.normpath(recipe['project_settings']['project_file'])
        temp_project = os.path.normpath(recipe['project_settings']['temp_project'])

        logger.info(f"Checking source project: {source_project}")

        if not os.path.exists(source_project):
            logger.error(f"Source project file not found: {source_project}")
            current_dir = os.getcwd()
            logger.error(f"Current directory: {current_dir}")
            aep_files = [f for f in os.listdir(current_dir) if f.endswith('.aep')]
            logger.error(f"Available .aep files: {aep_files}")
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
                          bar, monitor_stop_event, total_frames: int, progress_index: str, total_index: str,
                          result_dirs: List, logger=None, completion_flag=None):

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
                result_dir = get_rel_path(result_dirs[comp_idx], depth=-2)
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

def run_render_tasks(tasks: List[Dict[str, Any]], workers: int, logger, render_stop_event,
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
                            files_rendered, error_occurred = _process_completed_future(
                                remaining_future, remaining_task, j + 1, len(futures), results, logger, total_files_rendered, total_errors
                            )
                            total_files_rendered += files_rendered
                            if error_occurred:
                                total_errors += 1
                        except Exception as e:
                            total_errors += 1
                            task_detail = remaining_task.get('task_detail', remaining_task.get('comp_name', f'Task {j+1}'))
                            err_result = {
                                'success': False,
                                'task_id': j + 1,
                                'error_msg': f'Forced completion: {trace_error(e)}',
                                'files_rendered': 0,
                                'execution_time': 0.0
                            }
                            results.append(err_result)
                            logger.error(f'Task {j+1} forced completion failed ({task_detail}): {trace_error(e)}')
                    break

                try:
                    result = future.result(timeout=600)
                    future._cached_result = result
                    files_rendered, error_occurred = _process_completed_future(
                        future, task_info, i + 1, len(futures), results, logger, total_files_rendered, total_errors
                    )
                    total_files_rendered += files_rendered
                    if error_occurred:
                        total_errors += 1

                except Exception as e:
                    total_errors += 1
                    task_detail = task_info.get('task_detail', task_info.get('comp_name', f'Task {i+1}'))
                    err_result = {
                        'success': False,
                        'task_id': i + 1,
                        'error_msg': trace_error(e),
                        'files_rendered': 0,
                        'execution_time': 0.0
                    }
                    results.append(err_result)
                    logger.error(f'Task {i+1} failed ({task_detail}): {trace_error(e)}')

            success_count = len(results) - total_errors
            logger.info(f'All tasks completed: {len(results)} tasks, '
                      f'{total_files_rendered} files rendered, '
                      f'{success_count} success, {total_errors} errors')

    except Exception as e:
        logger.error(f'Multiprocessing execution failed: {trace_error(e)}')

    return results

def extract_temp_files(recipe: Dict[str, Any]) -> str:
    return recipe['project_settings']['temp_directory']

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
        logger.info('Execution mode: Multi composition sequential execution')

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
                        if '_' in chunk_id and chunk_id.count('_') >= 3:
                            parts = chunk_id.split('_')
                            if len(parts) >= 4:
                                start_frame = str(int(parts[-2]))
                                end_frame = str(int(parts[-1]))

                    file_count = task.get('file_count', 0)

                    task_num = f'RenderTask_{task_idx+1:02d}'

                    comp_tasks.append({
                        'comp_name': comp_name,
                        'aerender_command': task['aerender_command'],
                        'temp_project': recipe['project_settings']['temp_project'],
                        'task_detail': task_num,
                        'task_id': task_num,
                        'expected_files': file_count
                    })

            if not comp_tasks:
                logger.warning(f"No tasks found for composition: {comp_name}")
                continue

            total_frames = 0
            if 'frames' in comp_data:
                total_frames = len(comp_data['frames'])
            else:
                for task in comp_data['workflow']['chunk_tasks']:
                    total_frames += task.get('file_count', 0)

            comp_start_time = datetime.now()
            comp_end_time = comp_start_time

            try:
                with alive_bar(
                    total_frames, spinner=None, title='PLEASE WAIT…', title_length=27,
                    length=20, dual_line=True, stats=True, elapsed=True, manual=False,
                    enrich_print=False, force_tty=True, refresh_secs=0.1,
                    receipt_text=True, monitor_end=True
                ) as bar:
                    progress_index = f'{comp_index:02d}'
                    total_index = f'{total_comps:02d}'

                    bar.title = f'INITIALIZING… PLEASE WAIT… '
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

                    comp_start_time = datetime.now()

                    comp_results = run_render_tasks(comp_tasks, workers, logger, render_stop_event, bar, progress_index, total_index)
                    all_results.extend(comp_results)

                    comp_end_time = datetime.now()

                    time.sleep(0.5)

            except KeyboardInterrupt:
                logger.warning(f"Composition {comp_name} interrupted by user")
                time.sleep(0.2)
                raise
            except Exception as e:
                logger.error(f"Composition {comp_name} failed: {trace_error(e)}")
                time.sleep(0.2)
                raise

            comp_elapsed = comp_end_time - comp_start_time
            comp_elapsed_str = format_elapsed_time(comp_elapsed.total_seconds())

            if 'frames' in comp_data:
                for frame_num, frame_info in comp_data['frames'].items():
                    tmp_path = frame_info.get('tmp', '')
                    if tmp_path and os.path.exists(tmp_path):
                        frame_info['rendered'] = True

            frames = comp_data.get('frames', {})
            completed_count = sum(1 for frame in frames.values()
                                 if frame.get('rendered', False))

            recipe['result_outputs'][comp_name]['elapsed_time'] = comp_elapsed_str
            recipe['result_outputs'][comp_name]['completed'] = completed_count

            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(recipe, f, indent=2, ensure_ascii=False)
                logger.info(f"Composition completed: {comp_name} ({len(comp_results)} tasks, "
                           f"completed={completed_count}%, elapsed: {comp_elapsed_str})")
                logger.debug(f"JSON updated: {comp_name} completion status")
            except Exception as e:
                logger.warning(f"Failed to update completion status: {e}")

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

        temp_dir = extract_temp_files(recipe)
        return 0, temp_dir

    except Exception as e:
        err_msg = f"Render execution failed: {trace_error(e)}"
        try:
            logger.error(err_msg)
        except NameError:
            pass
        Msg.Error(err_msg)
        return 1, ""

def main():
    parser = argparse.ArgumentParser(description='AeRender v2.0 멀티 컴포지션 렌더링 실행기')
    parser.add_argument('json_path', help='JSON 레시피 파일 경로')
    parser.add_argument('-l', '--logs', action='store_true', help='로그 파일 생성')

    args = parser.parse_args()

    exit_code, temp_dir = execute_render(args.json_path, args.logs)
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
