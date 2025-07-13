import time, sys
import logging
from threading import Thread, Event
from typing import List, Union, Optional
from colorama import Fore, Back, Style, init
init(autoreset=True)

# COLORAMA:Available formatting constants are:
# Fore:BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Back:BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Style:DIM, NORMAL, BRIGHT, RESET_ALL


class ColorizeLogger:
    '''
    ◦ Apply log color based on log level.

    Args:
        record (logging.LogRecord): Log record.
        message (str): Log message.

    Returns:
        str

    Raise:
        None

    Examples:
        Colorize.format(record, message)
    '''

    LEVEL_COLORS={
        'DEBUG':Fore.GREEN,
        'INFO':Fore.WHITE,
        'WARNING':Fore.YELLOW,
        'ERROR':Fore.RED,
        'CRITICAL':Fore.MAGENTA,
    }

    @staticmethod
    def format(record:logging.LogRecord, message:str) -> str:
        """ Apply log color based on log level. """
        color=ColorizeLogger.LEVEL_COLORS.get(record.levelname, '')
        return f"{color}{message}{Style.RESET_ALL}"



class Msg:
    '''
    ◦ Set color for the output string using COLORAMA.

    Args:
        message (str)

    Returns:
        None
    '''

    # =========================================================================== #

    @staticmethod
    def Info(message:str):
        print(f'{Fore.GREEN}{Style.BRIGHT}INFO:{message}{Fore.RESET}{Back.RESET}')

    @staticmethod
    def Warning(message:str):
        print(f'{Back.YELLOW}{Fore.BLACK}WARNING:{message}{Fore.RESET}{Back.RESET}')

    @staticmethod
    def Confirm(message:str):
        print(f'{Back.CYAN}{Fore.BLACK}CONFIRM:{message}{Fore.RESET}{Back.RESET}')

    @staticmethod
    def Error(message:str, divide:bool=True):
        m = (f'{Back.RED}'
             f'{Fore.WHITE}'
             f'ERROR: {message}'
             f'{Fore.RESET}'
             f'{Back.RESET}'
        )
        m = f'-\n{m}\n-' if divide else m
        print(m)

    @staticmethod
    def Critical(message:str):
        print(f'{Back.RED}{Fore.BLACK}ERROR:{message}{Fore.RESET}{Back.RESET}')

    # =========================================================================== #

    @staticmethod
    def Dim(message: str, verbose: bool = False, flush: bool = False):
        res = f'{Style.DIM}{message}{Style.RESET_ALL}'
        if verbose:
            return res
        print(res, end='\r' if flush else '\n', flush=flush)
        return None

    @staticmethod
    def Alert(message:str, verbose:bool=False):
        res=f'{Fore.RED}{Style.BRIGHT}{message}{Style.RESET_ALL}{Fore.RESET}'
        return res if verbose else print(res)

    @staticmethod
    def Result(message:str, divide:bool=True, verbose:bool=False):
        m=(
            f'{Back.YELLOW}'
            f'{Fore.BLACK}'
            f'{message}'
            f'{Fore.RESET}'
            f'{Back.RESET}'
        )
        m = f'-\n{m}\n-' if divide else m
        return m if verbose else print(m)

    @staticmethod
    def _get_colored_message(message: str, fore_color: str, back_color: str = '',
                            verbose: bool = False, plain: bool = True,
                            flush: bool = False,
                            default_color: str = Fore.WHITE) -> str | None:
        '''
        ◦ Apply color and style to the message and return or print it.

        Args:
            message (str): The message to display.
            fore_color (str): Foreground color (e.g., Fore.RED). Used when plain=True.
            back_color (str): Background color (e.g., Back.RED). Optional.
            verbose (bool): If True, return the styled string; otherwise, print it.
            plain (bool):
                - True: Apply only foreground color (no background or BRIGHT style).
                - False: Apply background, default_color text, and BRIGHT style.
            default_color (str): Text color shown over background when plain=False
                                (default: Fore.WHITE).
        '''

        # When plain=True: Only the default foreground color is applied
        # (no background or bright colors).
        if plain:
            res = f'{fore_color}{message}{Fore.RESET}'
        else:
            back_start = back_color if back_color else ''
            back_end = Back.RESET if back_color else ''

            # When plain=False, control the text color with the default_color
            # parameter.
            res = (f'{back_start}{default_color}{Style.BRIGHT}{message}'
                f'{Style.RESET_ALL}{Fore.RESET}{back_end}')

        if verbose:
            return res

        # When verbose=False, it prints to the console.
        print(res, end='\r' if flush else '\n', flush=flush)
        return None  # Explicitly return None when printing to console


    @staticmethod
    def Red(message:str, verbose:bool=False, plain:bool=True, flush: bool=False):
        return Msg._get_colored_message(message, Fore.RED, Back.RED, verbose, plain, flush)

    @staticmethod
    def Yellow(message:str, verbose:bool=False, plain:bool=True, flush: bool=False):
        return Msg._get_colored_message(message, Fore.YELLOW, Back.YELLOW, verbose, plain, flush)

    @staticmethod
    def Green(message:str, verbose:bool=False, plain:bool=True, flush: bool=False):
        return Msg._get_colored_message(message, Fore.GREEN, Back.GREEN, verbose, plain, flush)

    @staticmethod
    def Blue(message:str, verbose:bool=False, plain:bool=True, flush: bool=False):
        return Msg._get_colored_message(message, Fore.BLUE, Back.BLUE, verbose, plain, flush)

    @staticmethod
    def Cyan(message:str, verbose:bool=False, plain:bool=True, flush: bool=False):
        return Msg._get_colored_message(message, Fore.CYAN, Back.CYAN, verbose, plain, flush)

    @staticmethod
    def Magenta(message:str, verbose:bool=False, plain:bool=True, flush: bool=False):
        return Msg._get_colored_message(message, Fore.MAGENTA, Back.MAGENTA, verbose, plain, flush)

    @staticmethod
    def White(message: str, verbose: bool = False, plain:bool=False, flush: bool=False):
        return Msg._get_colored_message(message, Fore.WHITE, Back.WHITE, verbose, plain, flush, default_color=Fore.BLACK)

    @staticmethod
    def Black(message: str, verbose: bool=False, plain: bool=True, flush: bool=False):
        res = f'{Back.WHITE}{Fore.BLACK}{message}{Fore.RESET}{Back.RESET}'
        if verbose:
            return res
        print(res, end='\r' if flush else '\n', flush=flush)
        return None

    # ========================= BLINK ========================= #


    @staticmethod
    # Added stop_event parameter
    def Blink(message: str, duration:float=30.0, interval:float=0.2,
              color:str='red', verbose:bool=False, clear_on_finish:bool=True,
              stop_event: Optional[Event] = None) -> None:

        '''
        ◦ Flashes a message in the terminal.

        Args:
            message (str): The message to flash.
            duration (float): Total time in seconds to keep flashing.
                              If no stop_event, flashing ends based on this value.
            interval (float): Interval in seconds for the message to appear and disappear.
            color (str): Name of a colorama.Fore color to use (e.g., "RED", "YELLOW").
            verbose (bool): If True, returns the color-applied string;
                            if False, flashes it in the console.
            clear_on_finish (bool): If True, clears the message after flashing stops;
                                    if False, leaves it.
            stop_event (Optional[threading.Event]): If this event is set,
                                                    flashing stops immediately.
        '''

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