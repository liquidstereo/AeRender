
import os, sys, errno, shutil
from os import PathLike
from pathlib import Path
from fnmatch import fnmatch
import re
import traceback
from typing import Union, List, Optional

from configs.render_config import RenderConfig
from configs import Msg, Logger

def abs_path(p: Path, normalize: bool = True) -> Path:
    if normalize:
        return os.path.abspath(p).replace(os.sep, '/')
    return str(os.path.abspath(p))

def get_rel_path(p: Path, depth: int=-1) -> str:
    r = os.path.normpath(str(p)).split(os.path.sep)
    return '/'.join(r[depth:])

def get_short_path(path: PathLike, base_dir: Union[str, Path] = 'results') -> str:
    p = Path(path)
    base = Path(base_dir)

    if base.is_absolute() and base in p.parents:
        return str(base.name / p.relative_to(base))

    for parent in p.parents:
        if parent.name == base_dir:
            return str(Path(parent.name) / p.relative_to(parent))

    return str(p)

def make_dir(p: Path) -> Path:
    if not isinstance(p, str):
        p = str(p)

    try:
        if not os.path.exists(p):
            os.makedirs(p)
    except OSError as e:
        Msg.Error(f'ERROR: "{p}"', e)
    return str(p)

def remove_exist(p: Path, logger: Logger) -> None:
    try:
        if os.path.isfile(p) or os.path.islink(p):
            os.remove(p)
            logger.debug_func_info(f'File removed: {p}')
        elif os.path.isdir(p):
            shutil.rmtree(p)
            logger.debug_func_info(f'Dir removed: {p}')
    except Exception:
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), str(p))

def list_files_in_dir(d: Path, **kwargs) -> List[str]:
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

def regex_string(s: str, pat: str, repl: str) -> str:
    return re.sub(pat, repl, s)

def sanitize_string(s: str, pattern: str = r'[\s/\\,]+', repl_string: str = '_') -> str:
    if isinstance(s, list) and s:
        s = s[0]
    s = str(s) if s is not None else ""

    return re.sub(r'[^\w]+', repl_string, s).strip(repl_string)

def trace_error(exc: Exception) -> str:
    try:
        tb = traceback.extract_tb(exc.__traceback__)[-1]
        filename = get_rel_path(tb.filename, depth=-2)
        return f'{filename}-{tb.name}:{tb.lineno}, msg={exc}'
    except Exception:
        return f'trace_error failed, msg={exc}'

def get_function_info() -> str:
    try:
        frame = traceback.extract_stack()[-2]
        filename = get_rel_path(frame.filename, depth=-2)
        return f"{filename}:{frame.lineno}:{frame.name}"
    except Exception:
        return "unknown_location"

def flush_lines(lines: int = 1) -> None:

    sys.stdout.write('\x1b[2K')
    sys.stdout.write('\r')

    if lines > 1:
        for _ in range(lines - 1):
            sys.stdout.write('\x1b[1A')
            sys.stdout.write('\x1b[2K')

    sys.stdout.flush()

def format_elapsed_time(elapsed_seconds: float) -> str:
    hours = int(elapsed_seconds // 3600)
    minutes = int((elapsed_seconds % 3600) // 60)
    seconds = int(elapsed_seconds % 60)
    milliseconds = int((elapsed_seconds % 1) * 1000)

    return f'{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}'
