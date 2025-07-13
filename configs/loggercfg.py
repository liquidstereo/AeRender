import os
from os import PathLike
import logging
from logging.handlers import (
    RotatingFileHandler, QueueHandler, QueueListener
)
import queue
import inspect


class CustomFormatter(logging.Formatter):
    '''
    ◦ Custom log formatter based on log level.

    Args:
        None

    Returns:
        str: Formatted log message string.

    Raise:
        None

    Examples:
        formatter = CustomFormatter()
        formatter.format(record)
    '''

    format_default = '%(asctime)s | %(levelname)-8s | %(message)s'
    format_custom = '%(message)s'
    format_debug = '%(message)s | %(asctime)s'

    logger_format = {
        logging.DEBUG: format_debug,
        logging.INFO: format_custom,
        logging.WARNING: format_default,
        logging.ERROR: format_default,
        logging.CRITICAL: format_default,
    }

    def format(self, record):
        log_fmt = self.logger_format.get(record.levelno)
        formatter = logging.Formatter(
            log_fmt, datefmt='%Y-%m-%d %H:%M:%S'
        )
        return formatter.format(record)


class Logger:
    '''
    ◦ Thread-safe logger with queue-based file handler.

    Args:
        name (str): Unique logger name.
        log_path (PathLike): Path to log file.

    Returns:
        Logger: Singleton logger instance.

    Raise:
        None

    Examples:
        log = Logger('app', 'app.log')
        log.info('message')
    '''

    _loggers = {}
    log_queue = queue.Queue(-1)

    def __new__(cls, name: str, log_path: PathLike):
        if name not in cls._loggers:
            cls._loggers[name] = super().__new__(cls)
        return cls._loggers[name]

    def __init__(self, name: str, log_path: PathLike):
        if hasattr(self, 'logger'):
            return
        self.logger = logging.getLogger(name)
        self.filepath = log_path
        self._init_logger()

    def _init_logger(self):
        '''
        ◦ Initialize logger with queue listener and rotating file handler.

        Args:
            None

        Returns:
            None

        Raise:
            None

        Examples:
            self._init_logger()
        '''
        if self.logger.hasHandlers():
            return

        self.logger.setLevel(logging.DEBUG)
        file_handler = RotatingFileHandler(
            self.filepath,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8-sig'
        )
        file_handler.setFormatter(CustomFormatter())
        queue_handler = QueueHandler(self.log_queue)
        self.logger.addHandler(queue_handler)
        listener = QueueListener(self.log_queue, file_handler)
        listener.start()

    def log(self, level: str, message: str, show_func_info: bool=False):
        '''
        ◦ General logging method with optional function info.

        Args:
            level (str): Log level string.
            message (str): Message to log.
            show_func_info (bool): Show function info (default: False)

        Returns:
            None

        Raise:
            None

        Examples:
            self.log('info', 'something happened')
        '''
        if self.logger.isEnabledFor(
            getattr(logging, level.upper(), logging.INFO)
        ):
            if show_func_info:
                frame = inspect.currentframe().f_back
                func = frame.f_code
                message = (
                    f'{message}\n{func.co_name} '
                    f'in "{func.co_filename}": {func.co_firstlineno}'
                )
            self.logger.log(
                getattr(logging, level.upper(), logging.INFO), message
            )

    def debug(self, message: str, show_func_info: bool=False):
        self.log('debug', message, show_func_info)

    def info(self, message: str, show_func_info: bool=False):
        self.log('info', message, show_func_info)

    def warning(self, message: str, show_func_info: bool=False):
        self.log('warning', message, show_func_info)

    def error(self, message: str, show_func_info: bool=False):
        self.log('error', message, show_func_info)

    def critical(self, message: str, show_func_info: bool=False):
        self.log('critical', message, show_func_info)