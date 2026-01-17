import os
from os import PathLike
import logging
import inspect
import traceback

class Logger:

    _loggers = {}

    def __new__(cls, name: str, log_path: PathLike):
        abs_path = os.path.abspath(str(log_path))
        unique_key = f'{name}_{abs_path}'.replace('\\', '/').replace(':', '_').replace('/', '_')

        if unique_key not in cls._loggers:
            cls._loggers[unique_key] = super().__new__(cls)
        return cls._loggers[unique_key]

    def __init__(self, name: str, log_path: PathLike):
        abs_path = os.path.abspath(str(log_path))

        if hasattr(self, 'logger') and hasattr(self, 'filepath'):
            existing_abs_path = os.path.abspath(str(self.filepath))
            if existing_abs_path == abs_path:
                return

        unique_logger_name = f'{name}_{abs_path}'.replace('\\', '/').replace(':', '_').replace('/', '_')

        self.logger = logging.getLogger(unique_logger_name)
        self.filepath = log_path

        self._init_logger()

    def _init_logger(self):
        if hasattr(self, 'logger') and self.logger:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
                handler.close()

        if hasattr(self, 'queue_listener') and self.queue_listener:
            self.queue_listener.stop()
            self.queue_listener = None

        self.logger = logging.getLogger(f'dummy_{id(self)}')
        self.logger.propagate = False
        self.logger.setLevel(logging.DEBUG)

    def __del__(self):
        pass

    def _get_relative_path(self, filepath: str) -> str:
        try:
            project_root = os.getcwd()
            rel_path = os.path.relpath(filepath, project_root)
            return rel_path.replace(os.path.sep, '/')
        except ValueError:
            return os.path.basename(filepath)

    def log(self, level: str, message: str, show_func_info: bool=False):
        if not message or not message.strip():
            return

        if show_func_info:
            try:
                frame = inspect.currentframe().f_back.f_back
                func = frame.f_code
                project_root = os.getcwd()
                rel_path = os.path.relpath(func.co_filename, project_root)
                rel_path = rel_path.replace(os.path.sep, '/')
                func_info = f'{rel_path}-{func.co_name}:{frame.f_lineno}'
                log_message = f'{func_info} | {message}'
            except:
                log_message = message
        else:
            log_message = message

        level_upper = level.upper()
        log_line = f'[{level_upper:<8}] {log_message}'

        try:
            with open(self.filepath, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except:
            pass

    def debug(self, message: str, show_func_info: bool=True):
        self.log('debug', message, show_func_info)

    def info(self, message: str, show_func_info: bool=True):
        self.log('info', message, show_func_info)

    def warning(self, message: str, show_func_info: bool=True):
        self.log('warning', message, show_func_info)

    def error(self, message: str, show_func_info: bool=True):
        self.log('error', message, show_func_info)

    def critical(self, message: str, show_func_info: bool=True):
        self.log('critical', message, show_func_info)

    def error_with_trace(self, exc: Exception, context: str = ''):
        tb = traceback.extract_tb(exc.__traceback__)[-1]
        rel_path = self._get_relative_path(tb.filename)
        line_number = tb.lineno
        func_name = tb.name

        error_msg = f'{context} - {rel_path}-{func_name}:{line_number}, msg={exc}'
        self.error(error_msg)

    def debug_func_info(self, message: str):
        frame = inspect.currentframe().f_back
        func = frame.f_code
        rel_path = self._get_relative_path(func.co_filename)
        func_info = f'{rel_path}-{func.co_name}:{frame.f_lineno}'
        self.debug(f'{func_info} | {message}')

    def info_execution(self, operation: str, status: str = 'in progress', message: str=None):
        self.info(f'{operation}: {status} | {message}' if message else f'{operation}: {status}')

class DummyLogger:
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def critical(self, *args, **kwargs): pass
    def log(self, *args, **kwargs): pass
    def debug_func_info(self, *args, **kwargs): pass
    def info_execution(self, *args, **kwargs): pass
    def error_with_trace(self, *args, **kwargs): pass
