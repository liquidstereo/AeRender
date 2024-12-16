import os
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from argparse import ArgumentParser
from alive_progress import alive_bar
from colorama import Fore, Back, Style, init
init(autoreset=True)

from scripts import abs_path, make_dir, remove_exist, pre_execute, \
    progress_bar, show_result, set_logger, job_info_msg, render_info_msg
from configs import Logger

# TODO 📌: AWAITING REFACTORING.

def get_output_files(comp: str, d: str|os.PathLike,
                     s: int, e: int) -> list[str|os.PathLike]:
    outputs = [(f'{comp}.{str(i).zfill(4)}.png') for i in range(s, e+1, 1)]
    outputs = [(os.path.join(d, f)) for f in outputs]
    reset_files = [remove_exist(f) for f in outputs] # REMOVE EXIST FILES
    outputs = [abs_path(f) for f in outputs]
    return outputs


# =========================================================================== #
# IMPORTANT:                                                                  #
# MAKE SURE THE "AERENDER.EXE" COMMAND IS PROPERLY SET IN THE SYSTEMS PATH    #
# =========================================================================== #
def render_sequence(fpath: str|os.PathLike,
                    output_path: list[str|os.PathLike],
                    comp_name: str,
                    rs_template: str, om_template: str, verbose_flag: str,
                    start_frame: int, end_frame: int, increment=1) -> str:

    command = (
        f'aerender -project \"{fpath}\" '
        f'-comp \"{comp_name}\" '
        f'-output \"{output_path}\" '
        f'-v \"{verbose_flag}\" '
        f'-RStemplate \"{rs_template}\" '
        f'-OMtemplate \"{om_template}\" '
        f'-s {start_frame} -e {end_frame} -i {increment}'
    )

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
        )
        if result.returncode == 0:
            return f'SUCCESS: {output_path}\n{result.stdout}'
        else:
            return f'ERROR: {output_path}\n{result.stderr}'
    except Exception as e:
        return f'EXCEPTION: {output_path}\n{str(e)}'


def exec_ae_render(fpath: str|os.PathLike,
                   comp_name: str,
                   rs_template: str, om_template: str, fext: str,
                   verbose_flag: str,
                   start_frame: int, end_frame: int,
                   per_task: int, workers: int,
                   output_dir: str|os.PathLike) -> None:

    stime = datetime.now()
    print('-')

    pre_execute(fpath)

    output_dir = make_dir(output_dir)
    output_files =  get_output_files(comp_name,
                                     output_dir,
                                     start_frame, end_frame)

    SYSTEM_WORKER = ProcessPoolExecutor()._max_workers
    if workers == 0 :
        JOB_WORKERS = SYSTEM_WORKER - 2
    else :
        JOB_WORKERS = min(SYSTEM_WORKER - 2, workers)

    logger, log_path = set_logger(output_dir, comp_name)
    job_info = job_info_msg(fpath, comp_name,
                            rs_template, om_template,
                            fext, verbose_flag,
                            start_frame, end_frame,
                            per_task, JOB_WORKERS,
                            output_dir)
    logger.info(job_info)

    total_length = len(output_files) + start_frame

    tasks = []
    output_format = f'{comp_name}.[####].{fext}' # SET_SEQUENCE_FORMATS
    output_path = abs_path(os.path.join(output_dir, output_format))

    for i in range(start_frame, total_length, per_task):
        start_index = i
        end_index = min(i + per_task - 1, total_length - 1)
        tasks.append((fpath, output_path, comp_name,
                      rs_template, om_template,
                      verbose_flag,
                      start_index, end_index))


    with ProcessPoolExecutor(max_workers=JOB_WORKERS) as executor:
        futures = {
            executor.submit(render_sequence, *task): task for task in tasks
        }
        progress_bar(output_files, logger)  # <-- PROGRESS
        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result()
            except Exception as e:
                err = f'Task failed for {task}: {e}'
                logger.error(err)
                print(f'{Back.RED}{err}{Back.RESET}')
                raise Exception(e)

    print('-')

    result, errors = show_result(fpath, comp_name, output_files, stime)
    render_info = render_info_msg(output_files, result, errors)
    logger.info(render_info)

    print('-')

    print(f'{Fore.YELLOW}DONE. PLEASE REFER TO LOG FILE. ({log_path}){Fore.RESET}')

    print('-')


def main(args):
    fpath = args.fpath
    comp_name = args.comp_name
    rs_template = args.rs_template
    om_template = args.om_template
    fext = args.file_extension
    verbose_flag = args.verbose_flag
    start_frame = args.start_frame
    end_frame = args.end_frame
    per_task = args.per_task
    workers = args.workers
    output_dir = args.output_dir

    exec_ae_render(fpath, comp_name,
                   rs_template, om_template,
                   fext,
                   verbose_flag,
                   start_frame, end_frame,
                   per_task, workers,
                   output_dir)


if __name__ == '__main__':
    parser = ArgumentParser(description='Render Adobe After Effects projects using Python.')
    parser.add_argument(
        '-f',
        '--fpath',
        type=str,
        default=None,
        required=True,
        help='INPUT PATH')

    parser.add_argument(
        '-c',
        '--comp_name',
        type=str,
        default=None,
        required=True,
        help='COMP NAME')

    parser.add_argument(
        '-rst',
        '--rs_template',
        type=str,
        default='Multi-Machine Settings',
        required=True,
        help='RENDER SETTINGS TEMPLATE')

    parser.add_argument(
        '-omt',
        '--om_template',
        type=str,
        default='Multi-Machine Sequence',
        required=True,
        help='OUTPUT MODULE TEMPLATE')

    parser.add_argument(
        '-x',
        '--file_extension',
        type=str,
        default='png',
        required=True,
        help='OUTPUT FILE EXTENSION')

    parser.add_argument(
        '-v',
        '--verbose_flag',
        type=str,
        default='ERRORS', # ERRORS or ERRORS_AND_PROGRESS
        required=False,
        help='VERBOSE FLAG')

    parser.add_argument(
        '-s',
        '--start_frame',
        type=int,
        default=0,
        required=True,
        help='START FRAME')

    parser.add_argument(
        '-e',
        '--end_frame',
        type=int,
        default=300,
        required=True,
        help='END FRAME')

    parser.add_argument(
        '-t',
        '--per_task',
        type=int,
        default=10,
        required=False,
        help='NUMBER OF PARALLEL TASKS')

    parser.add_argument(
        '-o',
        '--output_dir',
        type=str,
        default=None,
        required=True,
        help='OUTPUT DIR PATH')

    parser.add_argument(
        '-w',
        '--workers',
        type=int,
        default=0,
        required=False,
        help='workers')

    args = parser.parse_args()
    main(args)