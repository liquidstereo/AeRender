import os, sys, errno, shutil
from os import PathLike
from fnmatch import fnmatch
from typing import Union, List, Optional
import winreg

from configs import Msg, Logger

# TODO 📌: AWAITING REFACTORING.

def abs_path(p: PathLike, normalize: bool = True) -> PathLike:
    '''
    ◦ Convert path to absolute path with forward slashes.

    Args:
        p: dir / file path
        normalize: Normalize path (default: True)

    Returns:
        PathLike: absolute path

    Raise:
        None

    Examples:
        abs_path('C:/tmp')
        abs_path('C:/tmp', False)
    '''
    if normalize:
        return os.path.abspath(p).replace(os.sep, '/')
    return str(os.path.abspath(p))


def make_dir(p: PathLike) -> PathLike:
    '''
    ◦ Create directory if it doesn't exist.

    Args:
        p: dir path
    Returns:
        absolute path
    Raise:
        OSError: If error occurs during directory creation
    Examples:
        make_dir('C:/tmp')
        make_dir('C:/tmp/test')
    '''
    try:
        if not os.path.exists(p):
            os.makedirs(p)
    except OSError as e:
        Msg.Error(f'ERROR: "{p}"', e)
    return abs_path(p)


def remove_exist(p: PathLike) -> None:
    '''
    ◦ Remove file or directory if it exists.

    Args:
        p: dir / file path

    Returns:
        None

    Raise:
        OSError: If error occurs during file removal

    Examples:
        remove_exist('C:/tmp')
        remove_exist('C:/tmp/test')
    '''
    try:
        if os.path.isfile(p) or os.path.islink(p):
            os.remove(p)
        elif os.path.isdir(p):
            shutil.rmtree(p)
    except Exception:
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), str(p))


def exec_confirm(p: PathLike) -> bool:
    '''
    ◦ Prompt user to confirm deletion of subdirectories in output directory.

    Args:
        p: Path to the output directory

    Returns:
        bool: True if user confirms deletion (Y), False if user declines (N)

    Raise:
        FileNotFoundError: If the specified path does not exist

    Examples:
        exec_confirm('C:/output')
        exec_confirm(Path('/tmp/work'))
    '''
    p = abs_path(p)
    prompt = (f'Found existing subdirectories in output directory: "{p}"\n'
              f'These subdirectories may contain files from previous work '
              f'that encountered errors.\n').upper()
    prompt += Msg.Yellow('ALL EXISTING FILES MUST BE DELETED TO CONTINUE.\n\n',
                         verbose=True)

    prompt_confirm = 'Delete all files? (Y/N): '.upper()
    prompt_start = False
    try:
        while True:
            if not prompt_start :
                user_input = input(f'{prompt}{prompt_confirm}').lower().strip()
            else :
                user_input = input(f'{prompt_confirm}').lower().strip()

            if user_input == 'y':
                return True
            elif user_input == 'n':
                return False
            else:
                Msg.Dim('NOT AN APPROPRIATE CHOICE. PLEASE ENTER "Y" OR "N"')
                prompt_start = True

    except FileNotFoundError:
        Msg.Error(f'{p} DOES NOT EXISTS.')
        raise FileNotFoundError


def delete_all_subdirs(d: PathLike, logger) -> None:
    '''
    ◦ Delete all subdirectories in a directory after user confirmation.

    Args:
        d: Directory path to scan for subdirectories
        logger: Logger object for recording operations

    Returns:
        None

    Raise:
        SystemExit: If user declines to delete existing subdirectories

    Examples:
        delete_all_subdirs('C:/tmp', my_logger)
        delete_all_subdirs(Path('/output'), logger)
    '''
    d = abs_path(d)
    log_started = False
    confirmed = False

    for item in os.listdir(d):
        item_path = abs_path(os.path.join(d, item))

        if os.path.isdir(item_path):
            if not confirmed:
                if not exec_confirm(d):    # ← EXIST CONFIRM
                    error_msg = (f'OPERATION WILL NOT PROCEED WITHOUT DELETING '
                                 f'EXISTING FILES: {d}')
                    # Msg.Error(error_msg)
                    logger.error(error_msg)
                    sys.exit(1)    # ← sys.exit(0): 정상적인 종료 (성공) / sys.exit(1): 비정상적인 종료 (오류/실패)
                else:
                    confirmed = True

            if not log_started:
                logger.info('=' * 50)
                log_started = True

            try:
                shutil.rmtree(item_path)
                m = f'EXISTING "{item_path}" HAS BEEN REMOVED.'
                logger.info(m)

            except OSError as e:
                logger.error(f'ERROR DELETING {item_path}: {e}')

    if log_started:
        logger.info('=' * 50 + '\n')
    if confirmed :
        Msg.Black(f'REMOVED ALL SUBDIRECTORIES IN \"{d}\".')
        print(f'-')


def system_env_paths() -> List[str]:

    '''
    ◦ Get system environment paths (Windows only).

    Args:
        None

    Returns:
        sys_env_paths: List of system environment paths

    Raise:
        None

    Examples:
        system_env_paths()
    '''
    reg_path = (r'SYSTEM\CurrentControlSet\Control\Session Manager'
                r'\Environment')
    reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
    sys_env_paths = winreg.QueryValueEx(reg_key, 'Path')[0]
    return [p for p in sys_env_paths.split(';') if p]


def init_fpath(fpath: PathLike) -> bool:
    '''
    ◦ Check if file exists and raise error if not.

    Args:
        fpath: File path

    Returns:
        Boolean: True if file exists

    Raise:
        FileNotFoundError: If file does not exist

    Examples:
        init_fpath('C:/tmp')
    '''
    if not os.path.isfile(fpath):
        raise FileNotFoundError(f'NO SUCH FILE OR DIRECTORY: {fpath}')
    return True


def pre_execute(fpath: PathLike) -> bool:
    '''
    ◦ Check if file exists and After Effects is in PATH.

    Args:
        fpath: File path

    Returns:
        Boolean: True if file exists and After Effects is in PATH

    Raise:
        Exception: If After Effects is not in SYSTEM PATH

    Examples:
        pre_execute('C:/tmp')
    '''
    init_fpath(fpath)
    env_paths = system_env_paths()
    query_string = 'Adobe After Effects'
    query_result = list(filter(lambda c: query_string in c, env_paths))

    if not query_result:
        raise Exception(
            'MAKE SURE "aerender.exe" COMMAND IS PROPERLY SET '
            'IN THE SYSTEM\'S PATH'
        )
    return True


def list_files_in_dir(d: PathLike, **kwargs) -> List[str]:
    '''
    ◦ List files in directory with optional filtering.

    Args:
        d: Directory path to search
        kwargs (optional):
            - pat: File name pattern (default: '')
            - not: String or list of strings to exclude (default: [])

    Returns:
        List: List of absolute file paths

    Raise:
        OSError: If error occurs during file search

    Examples:
        list_files_in_dir('C:/tmp', pat='txt', not='dll')
    '''
    pat = kwargs.get('pat', '')
    exclude = kwargs.get('not', [])
    res = []

    if not isinstance(exclude, list):
        exclude = [exclude]

    try:
        for root, _, files in os.walk(d):
            for f in files:
                if (fnmatch(f, f'*{pat}*') and
                    not any(ex in f for ex in exclude)):
                    res.append(os.path.abspath(os.path.join(root, f)))
    except OSError as e:
        raise OSError(e.errno, os.strerror(e.errno), str(d)) from e

    return res



# ========================= AE.SPECIFICS ========================= #

def get_output_paths(comp: str, output_dir: str,
                     start: int, end: int, ext: str) -> List[PathLike]:
    '''
    ◦ Get output file paths.

    Args:
        comp: AE Composition name
        output_dir: Output directory path
        start: Start Frame
        end: End Frame

    Returns:
        List: List of output file paths

    Raise:
        None

    Examples:
        get_output_paths(comp_name,output_dir_path,1,100)
    '''
    return [
        abs_path(os.path.join(output_dir, f'{comp}.{i:04d}.{ext}'))
        for i in range(start, end + 1)
    ]


def rename_files(src_dir: PathLike, dst_dir: PathLike,
                 files: List[str], comp: str,
                 start: int,
                 logger: Logger) -> tuple[List[str], List[str]]:
    '''
    ◦ Rename and move files with sequential numbering.

    Args:
        src_dir: Source directory path
        dst_dir: Destination directory path
        files: File List
        comp: AE Composition name
        start: Start Frame
        logger: Logger object

    Returns:
        tuple:
            moved: List of moved file paths
            errors: List of error messages

    Raise:
        Exception: If error occurs during file operations

    Examples:
        rename_files('C:/tmp','D:/tmp',files,comp,start,logger)
    '''
    moved, errors = [], []

    for i, fname in enumerate(files):
        src = os.path.join(src_dir, fname)
        ext = fname.split('.')[-1]
        dst = os.path.join(dst_dir, f'{comp}.{start + i:04d}.{ext}')
        dst = dst.replace(os.sep, '/')

        try:
            if os.path.exists(dst):
                logger.info(f'Overwriting existing file: \"{dst}\"')    # ← ADD LOG MESSAGE
                os.remove(dst)
            os.rename(src, dst)
            moved.append(dst)
        except Exception as e:
            msg = f'Failed to move \"{src}\" → \"{dst}\": {e}'
            logger.error(msg)
            errors.append(msg)


    return moved, errors


def get_temp_name(comp: str, start: int, end: int) -> str:
    '''
    ◦ Generate temporary directory name.

    Args:
        comp: AE Composition name
        start: Start Frame
        end: End Frame

    Returns:
        tmp_dir: Temporary directory name

    Raise:
        None

    Examples:
        get_temp_name(comp,start,end)
    '''
    return f'tmp_{comp}_{start:04d}_{end:04d}'


def consolidate_outputs(out_dir: str, comp: str, start: int, end: int,
                       step: int, ext: str, logger) -> tuple[List[str],
                                                             List[str]]:
    '''
    ◦ Consolidate output files from temporary directories.

    Args:
        out_dir: Output directory path
        comp: AE Composition name
        start: Start Frame
        end: End Frame

    Returns:
        tuple:
            moved: List of moved file paths
            errors: List of error messages

    Raise:
        None

    Examples:
        consolidate_outputs('C:/tmp','ae_comp_name', 0, 100, 1, png, logger)
    '''
    moved, errors = [], []

    for i in range(start, end + 1, step):
        fs, fe = i, min(i + step - 1, end)
        tmp_dir = os.path.join(out_dir, get_temp_name(comp, fs, fe))

        if not os.path.exists(tmp_dir):
            logger.error(f'Missing temp: {tmp_dir}')
            continue

        files = sorted(
            f for f in os.listdir(tmp_dir) if f.lower().endswith(ext)
        )

        if not files:
            logger.error(f'Failed to locate {ext.upper()} file(s) in \"{tmp_dir}\"')
            try:
                os.rmdir(tmp_dir)
            except:
                pass
            continue

        m, e = rename_files(tmp_dir, out_dir, files, comp, fs, logger)
        moved.extend(m)
        errors.extend(e)

        moved = [(os.path.abspath(f).replace(os.sep, '/')) for f in moved]
        try:
            os.rmdir(tmp_dir)
        except:
            pass

    return moved, errors

# ========================= AE.SPECIFICS ========================= #