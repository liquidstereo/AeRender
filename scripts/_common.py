import os, sys, shutil, errno
from fnmatch import fnmatch
import winreg
from colorama import Fore, Back, Style, init
init(autoreset=True)

# TODO 📌: AWAITING REFACTORING.


def abs_path(p: str|os.PathLike, abs: bool=True) -> str|os.PathLike:
    return os.path.abspath(p).replace(os.sep, '/') if abs == True else p


def make_dir(p: str|os.PathLike) -> str|os.PathLike:
    try:
        if not os.path.exists(p): os.makedirs(p)
    except OSError as e:
        print(f'ERROR: \"{p}\"', e)
    return abs_path(p)


def remove_exist(p: str|os.PathLike) -> None:
    try:
        if os.path.isfile(p) or os.path.islink(p):
            os.remove(p)      # remove the file
        elif os.path.isdir(p):
            shutil.rmtree(p)  # remove dir and all contains
    except Exception as e:
        raise OSError(
            errno.ENOENT, os.strerror(errno.ENOENT), p)


# IMPORTANT ❗: WINDOWS ONLY
def system_env_paths() -> list[str]:
    reg_path = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
    reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
    sys_env_paths = winreg.QueryValueEx(reg_key, 'Path')[0]
    results = [p for p in sys_env_paths.split(';') if p != '']
    return results


def init_fpath(fpath: str|os.PathLike) -> bool:
    if not os.path.isfile(fpath) :
        e = (
            f'{Fore.RED}'
            f'NO SUCH FILE OR DIRECTORY: {fpath}'
            f'{Fore.RESET}'
        )
        raise FileNotFoundError(e)
    else :
        return True


def pre_execute(fpath: str|os.PathLike) -> bool:
    init_fpath(fpath)
    env_paths = system_env_paths()
    query_string = 'Adobe After Effects'
    query_result = list(filter(lambda c: query_string in c, env_paths))
    if not query_result :
        e = (
            f'{Fore.RED}'
            f'Make sure the \"aerender.exe\" command is '
            f'properly set in the system\'s PATH'
            f'{Fore.RESET}'
        )
        raise Exception(e)
    else :
        return True