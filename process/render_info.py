import os
from typing import Optional, Dict, List, Any, Union
from datetime import datetime

from configs import defaults, Msg
from configs.defaults import DEFAULT_FRAMES_PER_TASK, DEFAULT_SYSTEM_USAGE, DEFAULT_OUTPUT_DIR, DEFAULT_LOG_DIR, DEFAULT_JSON_DIR
from scripts import get_short_path, load_json_data, get_usable_workers, get_usable_cpu, get_usable_mem, format_elapsed_time
from process.render_logger import get_logger

def get_file_exists(file_path: str) -> tuple:
    if file_path and os.path.exists(file_path):
        return os.path.basename(file_path), 'Found'
    else:
        filename = os.path.basename(file_path) if file_path else 'Unknown'
        return filename, 'Not Found'

def normalize_frames(comps: list, starts: list, ends: list) -> tuple:
    comp_count = len(comps)

    if len(starts) < comp_count:
        last_start = starts[-1] if starts else 0
        starts.extend([last_start] * (comp_count - len(starts)))

    if len(ends) < comp_count:
        last_end = ends[-1] if ends else 0
        ends.extend([last_end] * (comp_count - len(ends)))

    return starts, ends

def calc_worker_count(args) -> int:
    user_workers = getattr(args, 'workers', 0)
    return user_workers if user_workers > 0 else get_usable_workers()

def calc_total_frames(comps: list, starts: list, ends: list) -> int:
    total_frames = 0
    for i in range(len(comps)):
        start = int(starts[i]) if i < len(starts) else 0
        end = int(ends[i]) if i < len(ends) else 0
        frames = max(0, end - start + 1) if end >= start else 0
        total_frames += frames
    return total_frames

def calc_system_usage(worker_count: int) -> float:
    max_cpu_workers = get_usable_cpu(default_usage = DEFAULT_SYSTEM_USAGE)
    max_mem_workers = get_usable_mem()
    cpu_usage = 0
    if max_cpu_workers > 0:
        cpu_usage = round((worker_count / max_cpu_workers) *
                         (DEFAULT_SYSTEM_USAGE * 100), 1)

    mem_usage = 0
    if max_mem_workers > 0:
        mem_usage = round((worker_count / max_mem_workers) *
                         (DEFAULT_SYSTEM_USAGE * 100), 1)
    return max(cpu_usage, mem_usage)

def format_args_info(args) -> list:
    lines = []

    fpath = getattr(args, 'fpath', '')
    if fpath:
        lines.append(f'Project File: {os.path.basename(fpath)}')

    comp = getattr(args, 'comp_name', [])
    if comp:
        if isinstance(comp, list):
            lines.append(f'Composition: {", ".join(comp)}')
        else:
            lines.append(f'Composition: {comp}')

    start = getattr(args, 'start', [])
    end = getattr(args, 'end', [])
    if start and end:
        if isinstance(start, list):
            start_str = ', '.join(map(str, start))
        else:
            start_str = str(start)
        if isinstance(end, list):
            end_str = ', '.join(map(str, end))
        else:
            end_str = str(end)
        lines.append(f'Frame Range: {start_str} ~ {end_str}')

    output = getattr(args, 'output_dir', None)
    if output:
        lines.append(f'Output Directory: {output}')

    workers = getattr(args, 'workers', 0)
    if workers > 0:
        lines.append(f'Worker Processes: {workers}')

    per_task = getattr(args, 'per_task', 0)
    if per_task > 0:
        lines.append(f'Frames Per Task: {per_task}')

    omt = getattr(args, 'om_template', '')
    if omt:
        lines.append(f'Output Module: {omt}')

    ext = getattr(args, 'ext', '')
    if ext:
        lines.append(f'File Extension: {ext}')

    preview = getattr(args, 'preview', False)
    lines.append(f'Preview Result: {preview}')

    logs = getattr(args, 'logs', False)
    lines.append(f'Generate Log: {logs}')

    save_json = getattr(args, 'save_json', False)
    lines.append(f'Save JSON: {save_json}')

    return lines

def show_execution_info(filename: str, comp_names: list, is_multi: bool,
                       total_frames: int, worker_count: int, total_tasks: int,
                       system_usage: float, args=None) -> None:
    msg = f'Render execution started for "{filename} - {", ".join(comp_names)}"'
    Msg.White(msg)

    task_info = 'Render.Task : '
    comp_str = 'Composition'
    if is_multi:
        task_info += f'{len(comp_names)} {comp_str}s'
    else:
        task_info += f'"{comp_names[0]}" {comp_str}'
    task_info += f', {total_frames} total frames'

    worker_info = (
        f'System.Usage: {worker_count} workers active, '
        f'{total_tasks} jobs pending, '
        f'{system_usage}% system load.'
    )

    Msg.Dim(task_info)
    Msg.Dim(worker_info)

    args_lines = format_args_info(args) if args else []

    return msg, task_info, worker_info, args_lines

def log_start_info(logger, msg: str, task_info: str,
                   worker_info: str, args_lines: list = None) -> None:
    if not logger:
        return

    try:
        logger.info(msg)
        logger.info(task_info)
        logger.info(worker_info)
        if args_lines:
            logger.info('Input Arguments:')
            for line in args_lines:
                logger.info(f'  - {line}')
    except Exception:
        pass

def render_start_info(args: Any, logger=None) -> None:
    file_path = getattr(args, 'fpath', '')
    filename, file_status = get_file_exists(file_path)

    compositions = getattr(args, 'comp_name', [])
    if isinstance(compositions, str):
        compositions = [compositions]

    start_frames = getattr(args, 'start', [])
    end_frames = getattr(args, 'end', [])

    if not isinstance(start_frames, list):
        start_frames = [start_frames]
    if not isinstance(end_frames, list):
        end_frames = [end_frames]

    start_frames, end_frames = normalize_frames(compositions,
                                               start_frames, end_frames)

    start_frame = int(start_frames[0]) if start_frames else 0
    end_frame = int(end_frames[0]) if end_frames else 0
    comp_render_frames = 0
    if end_frame >= start_frame:
        comp_render_frames = max(0, end_frame - start_frame + 1)

    worker_count = calc_worker_count(args)

    frames_per_task = DEFAULT_FRAMES_PER_TASK
    tasks_per_comp = 0
    if comp_render_frames > 0:
        tasks_per_comp = max(1, (comp_render_frames + DEFAULT_FRAMES_PER_TASK - 1)
                            // DEFAULT_FRAMES_PER_TASK)

    estimated_tasks = tasks_per_comp
    if len(compositions) > 0:
        estimated_tasks = tasks_per_comp * len(compositions)

    results_frames = calc_total_frames(compositions, start_frames, end_frames)
    comp_str = ', '.join(compositions) if compositions else ''

    output_dir = getattr(args, 'output', DEFAULT_OUTPUT_DIR)
    logs_enabled = getattr(args, 'logs', False)

    system_usage = calc_system_usage(worker_count)

    is_multi = len(compositions) > 1

    msg, task_info, worker_info, args_info = show_execution_info(
        filename, compositions, is_multi, results_frames,
        worker_count, estimated_tasks, system_usage, args)

    log_start_info(logger, msg, task_info, worker_info, args_info)

def extract_success_count(results: Dict[str, Any]) -> int:
    if not results:
        return 0

    success_count = results.get('total_moved', 0)
    if success_count == 0:
        possible_fields = ['successful_files', 'total_success', 'verified_files', 'file_count']
        for field in possible_fields:
            if field in results:
                return results[field]
    return success_count

def log_complete_info(logger, formatted_time: str, info: dict,
                     success_count: int, total_expected: int,
                     log_path: str, status: str) -> None:
    try:
        current_logger = get_logger()
        if current_logger:
            if len(info['output_dirs']) == 1:
                result_dir = info['output_dirs'][0]
            else:
                result_dir = f"{len(info['output_dirs'])} directories"

            current_logger.info(
                f'Process completed - elapsed: {formatted_time}, '
                f'Results: {success_count}/{total_expected} files, '
                f'Output: {result_dir}, Status: {status}')
    except Exception:
        pass

def extract_json_data(recipe_data: Dict[str, Any]) -> Dict[str, Any]:
    info = {}

    project_file = recipe_data.get('project_settings', {}).get('project_file', 'Unknown')
    info['filename'] = os.path.basename(project_file) if project_file else 'Unknown'

    result_outputs = recipe_data.get('result_outputs', {})
    info['comp_count'] = len(result_outputs)
    info['comp_names'] = list(result_outputs.keys())

    worker_config = recipe_data.get('worker_configuration', {})
    info['worker_count'] = worker_config.get('configured_workers', 0)

    rendering_options = recipe_data.get('rendering_options', {})
    info['save_json'] = rendering_options.get('save_json', False)
    info['enable_logging'] = rendering_options.get('enable_logging', False)
    info['json_path'] = rendering_options.get('json_path', False)
    info['log_path'] = rendering_options.get('log_path', False)

    total_frames = 0
    for comp_data in result_outputs.values():
        frames = comp_data.get('frames', {})
        total_frames += len(frames)
    info['total_frames'] = total_frames

    result_dirs = recipe_data.get('project_settings', {}).get('result_dir', ['results'])
    if isinstance(result_dirs, list):
        info['output_dirs'] = result_dirs if result_dirs else ['results']
    else:
        info['output_dirs'] = [result_dirs]

    return info

def render_complete_info(info_data: Optional[Dict[str, Any]],
                         results: Dict[str, Any],
                         elapsed_time: float,
                         logger=None) -> None:
    if info_data is None:
        info = {
            'filename': 'Unknown',
            'comp_count': 0,
            'comp_names': [],
            'worker_count': 0,
            'save_json': False,
            'enable_logging': False,
            'json_path': None,
            'log_path': None,
            'total_frames': 0,
            'output_dirs': ['results']
        }
    else:
        info = info_data
    formatted_time = format_elapsed_time(elapsed_time)
    success_count = extract_success_count(results)
    total_expected = info['total_frames']
    save_json = info['save_json']
    is_logged = info['enable_logging']
    json_path = info['json_path']
    log_path = info['log_path']

    overall_success = results.get('overall_success', False) if results else False
    status = 'SUCCESS' if overall_success else 'FAILED'

    filename = info['filename']
    output_dirs = info['output_dirs']

    output_dir_str = get_short_path(output_dirs[0], base_dir=DEFAULT_OUTPUT_DIR)

    render_msg = f'Render Completed ("{output_dir_str}"'
    if len(output_dirs) > 1:
        render_msg += f', {len(output_dirs)} Comps) '
    else:
        render_msg += f') '
    render_msg += f'Total Elapsed. {formatted_time} '

    Msg.Result(render_msg, divide=False)

    if save_json :
        print(f'-')
        path_str = get_short_path(json_path, base_dir='process')
        msg = (f'Render process info saved to file. '
               f'({path_str})')
        Msg.Dim(msg)

    if is_logged :
        path_str = get_short_path(log_path, base_dir='process')
        msg = (f'For More Details, Refer To Log File. '
               f'({path_str})')
        Msg.Dim(msg)

    log_path = None
    if logger and hasattr(logger, 'handlers'):
        for handler in logger.handlers:
            if hasattr(handler, 'baseFilename'):
                log_path = handler.baseFilename
                break

    log_complete_info(logger, formatted_time, info, success_count,
                      total_expected, log_path, status)
