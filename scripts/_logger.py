import os, sys
from os import PathLike
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from configs import Logger

def init_logger(fpath: PathLike) -> Logger:
    abs_path = os.path.abspath(fpath)
    logger_name = abs_path.replace('\\', '/').replace(':', '_').replace('/', '_')
    logger = Logger(logger_name, fpath)
    return logger

def set_log_path(d: PathLike, comp: str, comp_index: int = None,
                 total_comps: int = None, project_name: str = None) -> PathLike:
    from configs.defaults import DEFAULT_LOG_DIR
    log_dir = DEFAULT_LOG_DIR
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    safe_comp_name = "".join(c for c in comp if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_comp_name = safe_comp_name.replace(' ', '_')
    
    if project_name:
        safe_project_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_project_name = safe_project_name.replace(' ', '_')
        log_filename = f'{safe_project_name}_{safe_comp_name}.log'
    else:
        log_filename = f'{safe_comp_name}.log'

    p = os.path.abspath(os.path.join(log_dir, log_filename)).replace(os.sep, '/')

    
    return p

def clear_existing_log(log_path: PathLike) -> None:
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except:
            pass

def set_logger(d: PathLike, comp: str, comp_index: int = None,
               total_comps: int = None, project_name: str = None) -> tuple[Logger, PathLike]:
    log_path = set_log_path(d, comp, comp_index, total_comps, project_name)
    logger = init_logger(log_path)
    return logger, log_path

def job_info_msg(fpath: PathLike, comp_name: str,
                 rs_template: str, om_template: str,
                 fext: str, verbose_flag: str,
                 start_frame: int, end_frame: int,
                 per_task: int, workers: int,
                 output_dir: PathLike) -> str:

    datetime_now = datetime.now().replace(microsecond=0)
    info_msg = (
        f'{"="*50}\n'
        f'Rendering started for After Effects project (\"{fpath}\") '
        f'on {datetime_now}.\n'
        f'{"="*50}\n'
        f'Project File: {fpath}\n'
        f'Composition: {comp_name}\n'
        f'Render Settings: {rs_template}\n'
        f'Output Module: {om_template}\n'
        f'Verbose Flag: {verbose_flag}\n'
        f'Output To: \"{output_dir}\"\n'
        f'Start Frame: {start_frame}\n'
        f'End Frame: {end_frame}\n'
        f'Format: {fext.upper()}\n'
        f'Per Task: {per_task}\n'
        f'Workers: {workers}\n'
        f'{"="*50}'
    )
    return info_msg

def render_info_msg(output_files: list[PathLike],
                    etime: datetime,
                    errors:int) -> str:
    datetime_now = datetime.now().replace(microsecond=0)
    output_dir = os.path.dirname(output_files[0]) if output_files else "unknown"
    result_msg = (
        f'\n{"="*50}\n'
        f'Process Done. '
        f'(\"{output_dir}\", '
        f'{len(output_files)} Files, '
        f'{len(errors)} Error, '
        f'Elapsed time: {etime}) '
        f'on {datetime_now}\n'
        f'{"="*50}'
    )
    return result_msg

class DebugLogger:
    
    def __init__(self, name: str = "DebugLogger", file_path: PathLike = None):
        self.name = name
        self.file_path = file_path
        self.session_start = datetime.now()
        
    def info(self, message: str, show_func_info: bool = False):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}] INFO: {message}"
        
        if show_func_info:
            import inspect
            frame = inspect.currentframe().f_back
            func_name = frame.f_code.co_name
            line_num = frame.f_lineno
            log_msg += f" ({func_name}:{line_num})"
        
        print(log_msg)
        
        if self.file_path:
            self._write_to_file(log_msg)
    
    def debug(self, message: str, show_func_info: bool = False):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_msg = f"[{timestamp}] DEBUG: {message}"
        
        if show_func_info:
            import inspect
            frame = inspect.currentframe().f_back
            func_name = frame.f_code.co_name
            line_num = frame.f_lineno
            log_msg += f" ({func_name}:{line_num})"
        
        print(log_msg)
        
        if self.file_path:
            self._write_to_file(log_msg)
    
    def warning(self, message: str, show_func_info: bool = False):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}] WARNING: {message}"
        
        if show_func_info:
            import inspect
            frame = inspect.currentframe().f_back
            func_name = frame.f_code.co_name
            line_num = frame.f_lineno
            log_msg += f" ({func_name}:{line_num})"
        
        print(f"⚠️  {log_msg}")
        
        if self.file_path:
            self._write_to_file(log_msg)
    
    def error(self, message: str, show_func_info: bool = False):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}] ERROR: {message}"
        
        if show_func_info:
            import inspect
            frame = inspect.currentframe().f_back
            func_name = frame.f_code.co_name
            line_num = frame.f_lineno
            log_msg += f" ({func_name}:{line_num})"
        
        print(f"❌ {log_msg}")
        
        if self.file_path:
            self._write_to_file(log_msg)
    
    def _write_to_file(self, message: str):
        try:
            if self.file_path:
                with open(self.file_path, 'a', encoding='utf-8') as f:
                    f.write(f"{message}\n")
        except Exception as e:
            print(f"Log file write error: {e}")
    
    def trace_function(self, func_name: str, args: str = "", result: str = ""):
        if args:
            self.debug(f">>> {func_name}({args})", show_func_info=True)
        else:
            self.debug(f">>> {func_name}()", show_func_info=True)
            
        if result:
            self.debug(f"<<< {func_name} -> {result}", show_func_info=True)

def create_debug_logger(name: str = "AeRender", log_file: PathLike = None) -> DebugLogger:
    return DebugLogger(name, log_file)
