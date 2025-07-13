import os
from os import PathLike
import subprocess
import shutil

from scripts._common import make_dir, get_temp_name, delete_all_subdirs
from scripts._sig_handler import add_tracked_pid


def create_tasks(comp: str, output_dir: PathLike, start: int, end: int,
                 step: int, ext: str, fpath: str, rs: str, om: str,
                 verbose: str, logger):
    '''
    ◦ Create a list of AE render tasks per frame chunk.

    Args:
        comp: comp name
        output_dir: render output directory
        start: start frame
        end: end frame
        step: frame step
        ext: file extension
        fpath: AE project path
        rs: render settings template
        om: output module template
        verbose: verbosity level
        logger: logger instance

    Returns:
        list: list of task tuples

    Raise:
        None

    Examples:
        create_tasks('MyComp', './out', 0, 100, 10, 'png', ...)
    '''
    tasks = []
    total = end - start + 1
    delete_all_subdirs(output_dir, logger)    # ← REMOVE ALL SUB DIRs.
    for i in range(0, total, step):
        fs, fe = start + i, min(start + i + step - 1, end)
        tmp = os.path.join(output_dir, get_temp_name(comp, fs, fe))
        patt = os.path.join(make_dir(tmp), f'{comp}.[####].{ext}')
        tasks.append((fpath, patt, comp, rs, om, verbose, fs, fe))
    return tasks

def render_sequence(fpath: PathLike, pattern: str, comp: str, rs: str,
                    om: str, verbose: str, start: int,
                    end: int, i: int = 1):
    '''
    ◦ Run After Effects render sequence.

    Args:
        fpath: AE project path
        pattern: output file pattern
        comp: comp name
        rs: render settings template
        om: output module template
        verbose: verbosity level
        start: start frame
        end: end frame
        i: frame step (default 1)

    Returns:
        str: render result log

    Raise:
        None

    Examples:
        render_sequence(...)
    '''
    cmd = [
        'aerender', '-project', fpath, '-comp', comp,
        '-output', pattern, '-v', verbose,
        '-RStemplate', rs, '-OMtemplate', om,
        '-s', str(start), '-e', str(end), '-i', str(i)
    ]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True
        )
        add_tracked_pid(proc.pid)
        out, err = proc.communicate()
        if proc.returncode == 0:
            return f'SUCCESS: {start}-{end}\n{out}'
        return f'ERROR: {start}-{end}\n{err}'
    except KeyboardInterrupt:
        return f'USER INTERRUPTED: {start}-{end}'
    except Exception as e:
        return f'EXCEPTION: {start}-{end}\n{e}'

def remove_default_render_log(fpath: str, logger) -> PathLike | None:
    f = os.path.basename(fpath)
    d = os.path.dirname(fpath)
    log_dir = os.path.abspath(os.path.join(d, f + ' Logs'))

    if os.path.isdir(log_dir):
        shutil.rmtree(log_dir)
        msg = f'\nDefault render log directory removed: "{log_dir}"'
        logger.info(msg)
        return log_dir
    return None

def main():
    remove_default_render_log('test.aep')

if __name__ == '__main__':
    main()