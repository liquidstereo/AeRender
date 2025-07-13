import os, sys
from os import PathLike
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from configs import Logger


def init_logger(fpath: PathLike) -> Logger:
    '''
    ◦ Initialize logger.

    Args:
        fpath: log file path

    Returns:
        logger: logger object

    Raise:
        None

    Examples:
        init_logger('C:/tmp/logs.log')
    '''
    func_fpath=os.path.abspath(__file__)
    loggger = Logger(func_fpath, fpath)
    return loggger


def set_log_path(d: PathLike, comp: str) -> PathLike:
    '''
    ◦ Set log path.

    Args:
        d: log directory path
        comp: composition name

    Returns:
        p: log file path

    Raise:
        None

    Examples:
        set_log_path('C:/tmp', 'test')
    '''
    p = os.path.abspath(os.path.join(d, f'{comp}.log')).replace(os.sep, '/')
    if os.path.isfile(p) :
        os.remove(p)     # ← REMOVE THE LOG FILE IF IT EXISTS.
        pass
    return p


def set_logger(d: PathLike, comp: str) -> tuple[Logger, PathLike]:
    '''
    ◦ Set logger.

    Args:
        d: directory path
        comp: composition name

    Returns:
        tuple: logger object and log file path

    Raise:
        None

    Examples:
        set_logger('C:/tmp', 'test')
    '''
    log_path = set_log_path(d, comp)
    loggger = init_logger(log_path)
    return loggger, log_path


def job_info_msg(fpath: PathLike, comp_name: str,
                 rs_template: str, om_template: str,
                 fext: str, verbose_flag: str,
                 start_frame: int, end_frame: int,
                 per_task: int, workers: int,
                 output_dir: PathLike) -> str:
    '''
    ◦ Job info message.

    Args:
        fpath (PathLike): project file path
        comp_name (str): composition name
        rs_template (str): render settings template
        om_template (str): output module template
        fext (str): file extension
        verbose_flag (str): verbose flag
        start_frame (int): start frame
        end_frame (int): end frame
        per_task (int): per task
        workers (int): workers
        output_dir (PathLike): output directory path

    Returns:
        info_msg: job info message

    Raise:
        None

    Examples:
        job_info_msg('C:/tmp/test.aep', 'comp_name',
                     'rs_template', 'om_template', 'png',
                     'ERRORS', 1, 100, 1, 1, 'C:/tmp')
    '''

    datetime_now = datetime.now().replace(microsecond=0)
    info_msg = (
        f'{"="*50}\n'
        f'Rendering started for After Effects project (\"{fpath}\") '
        f'on {datetime_now}.\n'
        f'{"="*50}\n'
        f'Project File: {fpath}\n'
        f'Composition: {comp_name}\n'
        f'Render Settings: {rs_template}\n'
        f'Output Module: {om_template}\n'
        f'Verbose Flag: {verbose_flag}\n'
        f'Output To: \"{output_dir}\"\n'
        f'Start Frame: {start_frame}\n'
        f'End Frame: {end_frame}\n'
        f'Format: {fext.upper()}\n'
        f'Per Task: {per_task}\n'
        f'Workers: {workers}\n'
        f'{"="*50}\n'
    )
    return info_msg


def render_info_msg(output_files: list[PathLike],
                    etime: datetime,
                    errors:int) -> str:
    '''
    ◦ Render info message.

    Args:
        output_files: output files list
        etime: elapsed time
        errors: errors count

    Returns:
        result_msg: result message

    Raise:
        None

    Examples:
        render_info_msg(['C:/tmp/test.png'], datetime.now(), 0)
    '''
    datetime_now = datetime.now().replace(microsecond=0)
    output_dir = os.path.dirname(output_files[0])
    result_msg = (
        f'\n{"="*50}\n'
        f'Process Done. '
        f'(\"{output_dir}\", '
        f'{len(output_files)} Files, '
        f'{len(errors)} Error, '
        f'Elapsed time: {etime}) '
        f'on {datetime_now}\n'
        f'{"="*50}'
    )
    return result_msg