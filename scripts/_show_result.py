import os
from os import PathLike
from tabulate import tabulate
from datetime import datetime
import wcwidth
from typing import List

def pad_string_to_width(s: str, width: int, fillchar: str = ' ') -> str:
    '''
    ◦ Pads a string to a given display width, considering wide characters.

    If the string's display width is greater than the target width, it truncates
    the string with "...". This ensures consistent column width in terminal outputs.

    Args:
        s (str): The input string to pad or truncate.
        width (int): The target display width for the string.
        fillchar (str, optional): The character used for padding. Defaults to ' '.

    Returns:
        str: The padded or truncated string.

    Raise:
        None

    Examples:
        pad_string_to_width('Hello', 10) # -> 'Hello     '
        pad_string_to_width('안녕하세요', 5) # -> '안녕하...'
        pad_string_to_width('LongString', 5) # -> 'Lo...'
    '''
    ellipsis = '...'
    ellipsis_width = wcwidth.wcswidth(ellipsis)

    current_width = wcwidth.wcswidth(s)
    if current_width == -1:  # Handle unprintable characters
        return s.ljust(width, fillchar)

    if current_width > width:
        truncated_s = s
        target_content_width = width - ellipsis_width

        if target_content_width < 0:
            return ellipsis[:width] if width >= ellipsis_width else ellipsis[:width]

        while wcwidth.wcswidth(truncated_s) > target_content_width and len(truncated_s) > 0:
            truncated_s = truncated_s[:-1]
        return truncated_s + ellipsis
    else:
        return s + fillchar * (width - current_width)

# =========================================================================== #

def show_result(filepath: PathLike, comp_name: str,
                output_files: List[PathLike],
                invalid_images: List[PathLike] | None,
                stime: datetime) -> tuple[str, List[PathLike]]:
    '''
    ◦ Displays processing results using `tabulate` library.

    Args:
        filepath (str | os.PathLike): Path to the After Effects file.
        comp_name (str): Name of the composition processed.
        output_files (list[str]): List of expected output file paths.
        invalid_images (list[str] | None): List of paths to invalid image files, if any.
        stime (datetime): Start time of the process.

    Returns:
        tuple: A tuple containing (elapsed_time, error_files).
            elapsed_time (str): Formatted string of the elapsed time.
            error_files (list[str]): List of files that were not found or were invalid.

    Raise:
        None

    Examples:
        show_result('C:/tmp/test.aep', 'comp_name', ['C:/tmp/test.png'], None, datetime.now())
    '''
    MAX_WIDTH = 13    # ← MAX CELL WIDTH
    error_files = []
    for f in output_files:
        normalized_path = os.path.normpath(f)
        file_exists = os.path.isfile(normalized_path)
        if not file_exists:
            error_files.append(f)

    if invalid_images:
        error_files.extend(invalid_images)
    fn, ext = os.path.splitext(os.path.basename(filepath))
    elapsed = datetime.now() - stime
    elapsed = '{}'.format(elapsed)[:-3]
    header_list = [pad_string_to_width('AE.FILE', MAX_WIDTH),
                   pad_string_to_width('COMP', MAX_WIDTH),
                   pad_string_to_width('RESULTS', MAX_WIDTH),
                   pad_string_to_width('ERROR', MAX_WIDTH),
                   pad_string_to_width('ELAPSED.TIME', MAX_WIDTH)]    # ← HEADERs
    table = [[pad_string_to_width(fn+ext, MAX_WIDTH),
              pad_string_to_width(comp_name, MAX_WIDTH),
              pad_string_to_width(str(len(output_files))+' Files', MAX_WIDTH),
              pad_string_to_width(str(len(error_files)), MAX_WIDTH),
              pad_string_to_width(elapsed, MAX_WIDTH)]]
    print(tabulate(table,
                   headers=header_list,
                   tablefmt='outline',
                   stralign='left',
                   numalign='left'))
    return elapsed, error_files