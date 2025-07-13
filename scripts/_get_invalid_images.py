import os, sys, time
from os import PathLike
from PIL import Image, UnidentifiedImageError
from alive_progress import alive_bar

from configs import Msg
from scripts._common import remove_exist


def is_invalid_image(fpath: PathLike, min_size: int) -> tuple[bool, list[PathLike]]:
    '''
    ◦ Check if image file is invalid and return reasons.

    Args:
        fpath: file path
        min_size: minimum file size in bytes

    Returns:
        Tuple of (is_invalid, reasons)

    Raise:
        OSError: if file size error.

    Examples:
        is_invalid_image('C:/tmp/test.png', 1024)

    '''
    reasons = []

    # Check file size
    try:
        if os.path.getsize(fpath) < min_size:
            reasons.append('size too small')
    except OSError as e:
        reasons.append(f'file size error: {e}')
        return True, reasons

    # Check image integrity
    try:
        with Image.open(fpath) as img:
            img.verify()
    except (UnidentifiedImageError, OSError) as e:
        reasons.append(f'corrupt image: {e}')
        return True, reasons

    return bool(reasons), reasons


def _process_with_progress(files: list[PathLike], min_size: int) -> list[tuple]:
    '''
    ◦ PROCESS FILES WITH PROGRESS BAR.

    Args:
        files: file list
        min_size: minimum file size in bytes

    Returns:
        invalid_files: invalid file list

    Raise:
        None

    Examples:
        _process_with_progress(['C:/tmp/test.png'], 1024)
    '''
    invalid_files = []
    error_count = 0

    with alive_bar(len(files), title='PROCESSING⋯', dual_line=True,
                   stats=True, enrich_print=True) as bar:
        for fpath in files:
            fname = os.path.basename(fpath)
            is_invalid, reasons = is_invalid_image(fpath, min_size)

            if is_invalid:
                invalid_files.append((fpath, reasons))
                error_count += 1

            bar_text = f'CHECKED: {fname}'
            if error_count:
                bar_text += f' {error_count} ERROR(s)'
            bar.text = Msg.Dim(bar_text, verbose=True)
            bar()

        bar.title = 'PROCESS COMPLETED'

    return invalid_files


def _process_without_progress(files: list[PathLike], min_size: int) -> list[tuple]:
    '''
    ◦ PROCESS FILES WITHOUT PROGRESS BAR.

    Args:
        files: file list
        min_size: minimum file size in bytes

    Returns:
        invalid_files: invalid file list

    Raise:
        None

    Examples:
        _process_without_progress(['C:/tmp/test.png'], 1024)
    '''
    invalid_files = []

    for i, fpath in enumerate(files, 1):
        fname = os.path.basename(fpath)
        is_invalid, reasons = is_invalid_image(fpath, min_size)

        if is_invalid:
            invalid_files.append((fpath, reasons))

        Msg.Dim(f'VERIFYING IMAGES: {fname} '
                f'({i:04d}/{len(files):04d})', flush=True)

    time.sleep(0.25)
    print('\033[2K\r', end='')

    return invalid_files


def _write_log(invalid_files: list[tuple], log_path: PathLike, ext: str='png') -> None:
    '''
    ◦ WRITE INVALID FILES TO LOG FILE.

    Args:
        invalid_files: invalid file list
        log_path: log file path
        ext: file extension

    Returns:
        None

    Raise:
        None

    Examples:
        _write_log([('C:/tmp/test.png', ['size too small'])], 'C:/tmp/log.txt', 'png')
    '''
    if not invalid_files:
        return

    with open(log_path, 'w', encoding='utf-8') as f:
        for fpath, reasons in invalid_files:
            f.write(f'{fpath} → {", ".join(reasons)}\n')

    Msg.Red(f'INVALID {len(invalid_files)} {ext.upper()} FILES FOUND. '
            f'CHECK THE DETAILED LIST IN "{log_path}"')


def get_invalid_images(dpath: PathLike, files: list[PathLike], ext: str,
                       invalids_log: str='invalid_files.log',
                       min_file_size: int=1024,
                       progress: bool=False) -> tuple[list[str], str]:

    '''
    ◦ CHECK INVALID IMAGE FILES IN DIRECTORY / REMOVE SIG_HANDLER_LOG.

    Args:
        dpath: Directory path to scan
        ext: File extension to check
        invalids_log: Log file name for invalid files
        min_file_size: Minimum file size in bytes
        progress: Show progress bar

    Returns:
        Tuple of (invalid_files, log_path)

    Raise:
        None

    Examples:
        get_invalid_images('C:/tmp', 'png', 'invalid_files.log', 1024, True)
    '''
    dpath = os.path.realpath(dpath).replace(os.sep, '/')

    if not files:
        m = (
            f'FAILED TO FIND \"{ext}\" '
            f'FILEs IN \"{dpath}\" FOR VERIFYING.'
        )
        Msg.Error(m)
        return [], ''

    # Process files
    if progress:
        invalid_files = _process_with_progress(files, min_file_size)
    else:
        invalid_files = _process_without_progress(files, min_file_size)

    # Write log
    log_path = os.path.abspath(os.path.join(dpath, invalids_log))
    log_path = log_path.replace(os.sep, '/')
    _write_log(invalid_files, log_path, ext)

    sig_handler_log_path = './process_pids.log'
    remove_exist(sig_handler_log_path)    # ← REMOVE SIG_HANDLER_LOG

    return invalid_files, log_path


if __name__ == '__main__':
    get_invalid_images(r'__IMGs_DIR__')