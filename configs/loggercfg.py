import os
import logging
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
import queue
import inspect


class CustomFormatter(logging.Formatter):

    format_default = "%(asctime)s | %(levelname)-8s | %(message)s"
    format_custom = "%(message)s"
    format_debug = "%(message)s | %(asctime)s"

    FORMATS = {
        logging.DEBUG: format_debug,
        logging.INFO: format_custom,
        logging.WARNING: format_default,
        logging.ERROR: format_default,
        logging.CRITICAL: format_default,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


class Logger:
    _loggers = {}
    log_queue = queue.Queue(-1)

    def __new__(cls, name: str, log_path: str|os.PathLike):
        if name not in cls._loggers:
            cls._loggers[name] = super().__new__(cls)
        return cls._loggers[name]

    def __init__(self, name: str, log_path: str|os.PathLike):
        if hasattr(self, "logger"):
            return
        self.logger = logging.getLogger(name)
        self.filepath = log_path
        self._init_logger()

    def _init_logger(self):

        if not self.logger.hasHandlers():

            self.logger.setLevel(logging.DEBUG)

            file_handler = RotatingFileHandler(
                self.filepath, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8-sig'
            )
            file_handler.setFormatter(CustomFormatter())
            queue_handler = QueueHandler(self.log_queue)
            self.logger.addHandler(queue_handler)
            queue_listener = QueueListener(self.log_queue, file_handler)
            queue_listener.start()


    def log(self, level: str, msg: str, show_func_info: bool=False):
        if self.logger.isEnabledFor(getattr(logging, level.upper(), logging.INFO)):
            if show_func_info:
                frame = inspect.currentframe().f_back
                func = frame.f_code
                msg = f'{msg}\n{func.co_name} in "{func.co_filename}": {func.co_firstlineno}'
            self.logger.log(getattr(logging, level.upper(), logging.INFO), msg)

    def debug(self, msg: str, show_func_info: bool=False):
        self.log("debug", msg, show_func_info)

    def info(self, msg: str, show_func_info: bool=False):
        self.log("info", msg, show_func_info)

    def error(self, msg: str, show_func_info: bool=False):
        self.log("error", msg, show_func_info)

    def critical(self, msg: str, show_func_info: bool=False):
        self.log("critical", msg, show_func_info)