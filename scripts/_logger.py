import os, sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from configs import Logger


def init_logger(fpath: str|os.PathLike) -> Logger:
    func_fpath=os.path.abspath(__file__)
    loggger = Logger(func_fpath, fpath)
    return loggger


def set_log_path(d: str|os.PathLike, comp: str) -> str|os.PathLike:
    p = os.path.abspath(os.path.join(d, f'{comp}.log')).replace(os.sep, '/')
    if os.path.isfile(p) :
        os.remove(p)
    return p


def set_logger(d: str|os.PathLike, comp: str) -> Logger:
    log_path = set_log_path(d, comp)
    loggger = init_logger(log_path)
    return loggger, log_path


def job_info_msg(fpath: str|os.PathLike, comp_name: str,
                 rs_template: str, om_template: str,
                 fext: str, verbose_flag: str,
                 start_frame: int, end_frame: int,
                 per_task: int, workers: int,
                 output_dir: str|os.PathLike) -> str:

    datetime_now = datetime.now().replace(microsecond=0)
    info_msg = (
        f'Rendering started on {datetime_now} for project “{fpath}”\n\n'
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
        f'\n-\n'
    )
    return info_msg


def render_info_msg(output_files: list[str|os.PathLike],
                    etime: datetime,
                    errors:int) -> str:
    result_msg = (
        f'\n-\n'
        f'Process Done. '
        f'({len(output_files)} Files, '
        f'{len(errors)} Error, '
        f'Elapsed time: {etime})'
    )
    return result_msg