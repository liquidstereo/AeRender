
import time, sys
import logging
from threading import Thread, Event
import re
from typing import List, Union, Optional
from colorama import Fore, Back, Style, init
init(autoreset=True)

class ColorizeLogger:

    LEVEL_COLORS={
        'DEBUG':Fore.GREEN,
        'INFO':Fore.WHITE,
        'WARNING':Fore.YELLOW,
        'ERROR':Fore.RED,
        'CRITICAL':Fore.MAGENTA,
    }

    @staticmethod
    def format(record: logging.LogRecord, message: str) -> str:
        color=ColorizeLogger.LEVEL_COLORS.get(record.levelname, '')
        return f"{color}{message}{Style.RESET_ALL}"

class Msg:

    _last_was_flush = False

    @staticmethod
    def _clear_line():
        sys.stdout.write('\033[2K\r')
        sys.stdout.flush()

    @staticmethod
    def _handle_flush():
        if Msg._last_was_flush:
            Msg._clear_line()
            Msg._last_was_flush = False

    @staticmethod
    def _transform_message(msg: str, upper: bool=True) -> str:

        patterns = [
            r'\{[^}]+\}',
            r'"[^"]*"',
            r"'[^']*'",
            r'\[[^\]]*\]',
            r'\([^\)]*\)',
            r'\S*[\\/]\S*'
        ]

        combined = '|'.join(f'({p})' for p in patterns)

        tokens = re.split(combined, msg)

        res = []
        for token in tokens:
            if not token:
                continue

            if re.fullmatch(combined, token):
                res.append(token)
            else:
                res.append(token.upper() if upper else token)

        return ''.join(res)

    @staticmethod
    def _apply_common_formatting(message: str,
                                 divide: bool, upper: bool) -> str:
        message = Msg._transform_message(message, upper)
        return message

    @staticmethod
    def _apply_color_formatting(message: str,
                                fore_color: str, back_color: str = '',
                                default_fg_color: str = Fore.WHITE,
                                default_bg_color: str = Back.WHITE,
                                plain: bool = True,
                                flush: bool = False,
                                verbose: bool = False,
                                divide: bool = False) -> str | None:
        colored_message = Msg._get_colored_message(message,
                                                   fore_color, back_color,
                                                   default_fg_color,
                                                   default_bg_color,
                                                   plain, False, True)

        if divide:
            colored_message = (
                f'{Fore.WHITE}-{Style.RESET_ALL}\n'
                f'{Style.BRIGHT}{colored_message}{Style.RESET_ALL}\n'
                f'{Fore.WHITE}-{Style.RESET_ALL}'
            )

        if verbose:
            return colored_message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(colored_message, end='\r' if flush else '\n', flush=flush)
        return None

    @staticmethod
    def _get_colored_message(message: str,
                             fore_color: str, back_color: str = '',
                             default_fg_color: str = Fore.WHITE,
                             default_bg_color: str = Back.WHITE,
                             plain: bool=True,
                             flush: bool=False,
                             verbose: bool=False) -> str | None:

        if plain:
            res = f'{Style.BRIGHT}{fore_color}{message}{Style.RESET_ALL}'
        else:
            bg_color = back_color if back_color else default_bg_color

            if back_color == default_bg_color :
                res = (f'{bg_color}{default_fg_color}{message}'
                       f'{Style.RESET_ALL}')
            else :
                res = (f'{bg_color}{default_fg_color}{Style.BRIGHT}{message}'
                       f'{Style.RESET_ALL}')

        if verbose:
            return res

        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        print(res, end='\r' if flush else '\n', flush=flush)
        return None

    @staticmethod
    def Info(message: str, divide: bool=True, upper: bool=True,
             verbose: bool=False, flush: bool=False):
        message = Msg._transform_message(message, upper)

        message = (f'{Fore.GREEN}{Style.BRIGHT}'
                   f'INFO: {message}'
                   f'{Fore.RESET}{Back.RESET}'
        )
        message = f'-\n{message}\n-' if divide else message
        if verbose:
            return message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(message, end='\r' if flush else '\n', flush=flush)

    @staticmethod
    def Debug(message: str, divide: bool=False, upper: bool=True,
             verbose: bool=False, flush: bool=False):
        message = Msg._transform_message(message, upper)

        message = (f'{Fore.WHITE}{Style.BRIGHT}'
                   f'DEBUG: {message}'
                   f'{Fore.RESET}{Back.RESET}'
        )
        message = f'-\n{message}\n-' if divide else message
        if verbose:
            return message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(message, end='\r' if flush else '\n', flush=flush)

    @staticmethod
    def Warning(message: str, divide: bool=True, upper: bool=True,
                verbose: bool=False, flush: bool=False):
        message = Msg._transform_message(message, upper)

        message = (f'{Fore.YELLOW}'
                   f'WARNING: {message}'
                   f'{Style.RESET_ALL}'
        )
        message = f'-\n{message}\n-' if divide else message
        if verbose:
            return message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(message, end='\r' if flush else '\n', flush=flush)

    @staticmethod
    def Confirm(message: str, divide: bool=False, upper: bool=True,
                verbose: bool=False, flush: bool=False):
        message = Msg._transform_message(message, upper)

        message = (f'{Style.BRIGHT}{Fore.CYAN}'
                   f'CONFIRM: {message}'
                   f'{Style.RESET_ALL}')
        message = f'-\n{message}\n-' if divide else message
        if verbose:
            return message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(message, end='\r' if flush else '\n', flush=flush)

    @staticmethod
    def Error(message: str, divide: bool=True, upper: bool=True,
              verbose: bool=False, flush: bool=False):
        message = Msg._transform_message(message, upper)

        message = (f'{Back.RED}{Fore.WHITE}'
                   f'ERROR: {message}'
                   f'{Style.RESET_ALL}'
        )
        message = f'-\n{message}\n-' if divide else message
        if verbose:
            return message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(message, end='\r' if flush else '\n', flush=flush)

    @staticmethod
    def Critical(message: str, divide: bool=True, upper: bool=True,
                 verbose: bool=False, flush: bool=False):
        message = Msg._transform_message(message, upper)

        message = (f'{Back.RED}{Fore.WHITE}'
                   f'CRITICAL: {message}'
                   f'{Style.RESET_ALL}'
        )
        message = f'-\n{message}\n-' if divide else message
        if verbose:
            return message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(message, end='\r' if flush else '\n', flush=flush)

    @staticmethod
    def Dim(message: str, divide: bool=False, upper: bool=True,
            flush: bool=False, verbose: bool=False) -> str | None:
        message = Msg._transform_message(message, upper)
        message = Msg._apply_common_formatting(message, divide, upper)
        styled_message = (f'{Style.DIM}'
                         f'{message}'
                         f'{Style.RESET_ALL}')

        if verbose:
            return styled_message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(styled_message, end='\r' if flush else '\n', flush=flush)
        return None

    @staticmethod
    def Alert(message: str, divide: bool=True, upper: bool=True,
              flush: bool=False, verbose: bool=False) -> str | None:
        message = Msg._transform_message(message, upper)
        styled_message = (f'{Fore.RED}'
                         f'ALERT: {message}'
                         f'{Style.RESET_ALL}')
        styled_message = f'-\n{styled_message}\n-' if divide else styled_message

        if verbose:
            return styled_message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(styled_message, end='\r' if flush else '\n', flush=flush)
        return None

    @staticmethod
    def Result(message: str, divide: bool=True, upper: bool=True,
               flush: bool=False, verbose: bool=False) -> str | None:
        message = Msg._transform_message(message, upper)
        styled_message = (f'{Back.YELLOW}{Fore.BLACK}'
                         f'RESULT: {message}'
                         f'{Style.RESET_ALL}')
        styled_message = f'-\n{styled_message}\n-' if divide else styled_message

        if verbose:
            return styled_message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(styled_message, end='\r' if flush else '\n', flush=flush)
        return None

    @staticmethod
    def Red(message: str, divide: bool=False, upper: bool=True, flush: bool=False, verbose: bool=False, plain: bool=True):
        message = Msg._apply_common_formatting(message, divide, upper)
        return Msg._apply_color_formatting(message, Fore.RED, Back.RED, Fore.WHITE, Back.WHITE, plain, flush, verbose, divide)

    @staticmethod
    def Yellow(message: str, divide: bool=False, upper: bool=True, flush: bool=False, verbose: bool=False, plain: bool=True):
        message = Msg._apply_common_formatting(message, divide, upper)
        return Msg._apply_color_formatting(message, Fore.YELLOW, Back.YELLOW, Fore.WHITE, Back.WHITE, plain, flush, verbose, divide)

    @staticmethod
    def Green(message: str, divide: bool=False, upper: bool=True, flush: bool=False, verbose: bool=False, plain: bool=True):
        message = Msg._apply_common_formatting(message, divide, upper)
        return Msg._apply_color_formatting(message, Fore.GREEN, Back.GREEN, Fore.WHITE, Back.WHITE, plain, flush, verbose, divide)

    @staticmethod
    def Blue(message: str, divide: bool=False, upper: bool=True, flush: bool=False, verbose: bool=False, plain: bool=True):
        message = Msg._apply_common_formatting(message, divide, upper)
        return Msg._apply_color_formatting(message, Fore.BLUE, Back.BLUE, Fore.WHITE, Back.WHITE, plain, flush, verbose, divide)

    @staticmethod
    def Cyan(message: str, divide: bool=False, upper: bool=True, flush: bool=False, verbose: bool=False, plain: bool=True):
        message = Msg._apply_common_formatting(message, divide, upper)
        return Msg._apply_color_formatting(message, Fore.CYAN, Back.CYAN, Fore.WHITE, Back.WHITE, plain, flush, verbose, divide)

    @staticmethod
    def Magenta(message: str, divide: bool=False, upper: bool=True, flush: bool=False, verbose: bool=False, plain: bool=True):
        message = Msg._apply_common_formatting(message, divide, upper)
        return Msg._apply_color_formatting(message, Fore.MAGENTA, Back.MAGENTA, Fore.WHITE, Back.WHITE, plain, flush, verbose, divide)

    @staticmethod
    def Plain(message: str, divide: bool=False, upper: bool=True, flush: bool=False, verbose: bool=False, plain: bool=True):
        message = Msg._apply_common_formatting(message, divide, upper)

        if divide:
            message = f'{Fore.WHITE}-{Style.RESET_ALL}\n{message}\n{Fore.WHITE}-{Style.RESET_ALL}'

        if verbose:
            return message
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(message, end='\r' if flush else '\n', flush=flush)
        return None

    @staticmethod
    def White(message: str, divide: bool=False, upper: bool=True, flush: bool=False, verbose: bool=False, plain: bool=False):
        message = Msg._apply_common_formatting(message, divide, upper)
        return Msg._apply_color_formatting(message, Fore.BLACK, Back.WHITE, Fore.BLACK, Back.WHITE, plain, flush, verbose, divide)

    @staticmethod
    def Black(message: str, divide: bool=False, upper: bool=True, flush: bool=False, verbose: bool=False, plain: bool=True):
        message = Msg._apply_common_formatting(message, divide, upper)
        return Msg._apply_color_formatting(message, Fore.BLACK, Back.BLACK, Fore.WHITE, Back.BLACK, plain, flush, verbose, divide)

    @staticmethod
    def Blink(message: str, duration: float = 30.0, interval: float = 0.2,
              color: str = 'red', verbose: bool=False, clear_on_finish: bool=True,
              stop_event: Optional[Event] = None, upper: bool=False) -> None:

        message = Msg._transform_message(message, upper)

        if verbose:
            try:
                actual_fore_color = getattr(Fore, color.upper())
            except AttributeError:
                actual_fore_color = Fore.RESET
            return f"{actual_fore_color}{message}{Fore.RESET}"

        end_time = time.time() + duration

        try:
            current_color_start = getattr(Fore, color.upper())
        except AttributeError:
            current_color_start = Fore.RESET

        while (stop_event is None and time.time() < end_time) or \
              (stop_event is not None and not stop_event.is_set()):

            sys.stdout.write(f"{current_color_start}{message}\r")
            sys.stdout.flush()

            if stop_event and stop_event.wait(interval):
                break

            sys.stdout.write(f"\r{' ' * len(message)}\r")
            sys.stdout.flush()

            if stop_event and stop_event.wait(interval):
                break

        time.sleep(0.1)

        if clear_on_finish:
            sys.stdout.write("\033[2K\r")
            sys.stdout.flush()
        else:
            sys.stdout.write(f"{current_color_start}{message}{Style.RESET_ALL}\n")
            sys.stdout.flush()
