
import os
from typing import Dict, Any

from configs.loggercfg import DummyLogger
from scripts._logger import set_logger

_current_logger = None

def extract_project_info(recipe_data: Dict[str, Any]) -> tuple:
    project_file = os.path.splitext(
        os.path.basename(recipe_data['project_settings']['project_file'])
    )[0]
    comp_names = list(recipe_data['result_outputs'].keys())
    comp_name = comp_names[0] if len(comp_names) == 1 else 'Comps'
    return project_file, comp_names, comp_name

def extract_args_info(args: Any) -> tuple:
    file_path = getattr(args, 'fpath', '')
    project_file = (os.path.splitext(os.path.basename(file_path))[0] 
                   if file_path else 'Unknown')
    
    compositions = getattr(args, 'comp_name', [])
    if isinstance(compositions, str):
        compositions = [compositions]
    
    comp_name = compositions[0] if len(compositions) == 1 else 'Comps'
    return project_file, compositions, comp_name

def get_logger():
    global _current_logger
    return _current_logger if _current_logger else DummyLogger()

def logger_init(args: Any, recipe_data: Dict[str, Any] = None, 
               clear_existing: bool = False):
    try:
        from configs import defaults
        
        if recipe_data:
            project_file, comp_names, comp_name = extract_project_info(recipe_data)
            output_dir = get_output_dir(recipe_data, comp_names, defaults)
        else:
            project_file, _, comp_name = extract_args_info(args)
            output_dir = defaults.DEFAULT_OUTPUT_DIR
            
        logger, log_path = set_logger(output_dir, comp_name, 0, 1, project_file)
        
        if clear_existing:
            from scripts._logger import clear_existing_log
            clear_existing_log(log_path)
        
        global _current_logger
        _current_logger = logger
        
        return logger
        
    except Exception:
        return DummyLogger()

def get_output_dir(recipe_data: Dict[str, Any], comp_names: list, 
                  defaults) -> str:
    result_dirs = recipe_data['project_settings']['result_dir']
    
    if len(comp_names) == 1:
        return (result_dirs[0] if isinstance(result_dirs, list) 
                else result_dirs)
    else:
        return defaults.DEFAULT_OUTPUT_DIR

def render_info_log(recipe: Dict[str, Any], enable_logs: bool, 
                   preview: bool, logger) -> None:
    try:
        project_file = os.path.basename(
            recipe['project_settings']['project_file']
        )
        comp_names = list(recipe['result_outputs'].keys())
        total_files = calc_total_files(recipe)
        workers = recipe['worker_configuration']['configured_workers']
        total_tasks = calc_total_tasks(recipe)

        logs_status = 'enabled' if enable_logs else 'disabled'
        preview_status = 'enabled' if preview else 'disabled'
        
        logger.info(
            f"Render started. File: {project_file}, "
            f"Compositions: {', '.join(comp_names)}, "
            f"Total frames: {total_files}, "
            f"Tasks: {total_tasks}, "
            f"Workers: {workers}, "
            f"Logs: {logs_status}, "
            f"Preview: {preview_status}"
        )

    except Exception:
        pass

def calc_total_files(recipe: Dict[str, Any]) -> int:
    return sum(len(comp_data.get('frames', {})) 
               for comp_data in recipe['result_outputs'].values())

def calc_total_tasks(recipe: Dict[str, Any]) -> int:
    total_tasks = 0
    for comp_data in recipe['result_outputs'].values():
        if 'workflow' in comp_data and 'chunk_tasks' in comp_data['workflow']:
            total_tasks += len(comp_data['workflow']['chunk_tasks'])
    return total_tasks

def render_result_log(json_path: str, logger) -> None:
    try:
        from scripts._ae_specifics import load_json_data
        recipe = load_json_data(json_path)
        
        project_file = os.path.basename(
            recipe['project_settings']['project_file']
        )
        comp_names = list(recipe['result_outputs'].keys())
        total_files = calc_total_files(recipe)
        
        total_elapsed_str = calc_total_elapsed_time(recipe)

        logger.info(
            f"Render completed - {project_file}: {', '.join(comp_names)} "
            f"({total_files} files, elapsed: {total_elapsed_str})"
        )

    except Exception:
        pass

def calc_total_elapsed_time(recipe: Dict[str, Any]) -> str:
    total_seconds = 0
    
    for comp_data in recipe['result_outputs'].values():
        elapsed_str = comp_data.get('elapsed_time', '0:00:00')
        try:
            time_parts = elapsed_str.split(':')
            if len(time_parts) == 3:
                hours = int(time_parts[0])
                minutes = int(time_parts[1])
                seconds_str = time_parts[2]
                seconds = (float(seconds_str) if '.' in seconds_str 
                          else int(seconds_str))
                total_seconds += hours * 3600 + minutes * 60 + seconds
        except:
            continue

    from scripts._common import format_elapsed_time
    return format_elapsed_time(total_seconds)

def get_current_log_path() -> str:
    try:
        logger = get_logger()
        if not logger or not hasattr(logger, 'handlers'):
            return None
            
        for handler in logger.handlers:
            if hasattr(handler, 'baseFilename'):
                return handler.baseFilename
        
        return None
    except Exception:
        return None
