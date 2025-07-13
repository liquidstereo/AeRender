import os
import sys
from os import PathLike
import time
from threading import Event
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from argparse import ArgumentParser
import multiprocessing as mp
from typing import List
from dataclasses import dataclass

from alive_progress import alive_bar

from scripts import (
    abs_path, make_dir, pre_execute, show_result, set_logger, get_output_paths,
    consolidate_outputs, job_info_msg, render_info_msg,
    activate_system_monitor, progress_file_monitor,
    get_usable_workers, get_invalid_images, setup_handler,
    create_tasks, render_sequence, worker_handler, preview_result,
    remove_default_render_log
)
from configs import Msg


@dataclass
class RenderConfig:
    """
    ◦ Stores and manages all settings required for the After Effects rendering process.

    This data class is initialized via CLI arguments or direct instantiation,
    and serves to pass consistent configuration values across various functions
    in the rendering pipeline.

    Attributes:
        fpath (PathLike): Absolute path to the AE project file.
        comp_name (str): Name of the composition to render.
        output_dir (PathLike): Absolute path to the directory where the final output will be saved.
        start (int): Starting frame of the render sequence.
        end (int): Ending frame of the render sequence.
        workers (int): Number of rendering processes (workers) to use. 0 for auto-detection.
        per_task (int): Number of frames a single worker processes at once. 0 for auto-calculation.
        rs_template (str): Name of the Render Settings preset to use.
        om_template (str): Name of the Output Module preset to use.
        ext (str): File extension for the output image sequence (e.g., 'png', 'jpg').
        verbose (str): Logging level flag to pass to the After Effects engine.
        preview (bool): Whether to preview the result after rendering is complete.
    """
    fpath: PathLike
    comp_name: str
    output_dir: PathLike
    start: int
    end: int
    workers: int
    per_task: int
    rs_template: str
    om_template: str
    ext: str
    verbose: str
    preview: bool

    def __post_init__(self):
        """Normalizes paths and creates the output directory after initialization."""
        self.fpath = abs_path(self.fpath)
        self.output_dir = make_dir(self.output_dir)


def setup_render(config: RenderConfig):
    """
    ◦ Sets up the initial environment for rendering.

    This function is responsible for the preparation phase of the rendering process,
    including log file creation, error handler setup, and project file validation.

    Args:
        config (RenderConfig): An object containing all necessary rendering settings.

    Returns:
        logging.Logger: The configured logger object, which records all logs during the rendering process.
    """
    logger, log_path = set_logger(config.output_dir, config.comp_name)
    setup_handler(logger)
    pre_execute(config.fpath)
    return logger


def execute_rendering(config: RenderConfig, logger):
    """
    ◦ Executes the actual rendering tasks using multiprocessing.

    This function is responsible for the core execution phase of rendering.
    It distributes tasks based on system specifications and settings,
    creates a process pool to perform rendering in parallel, and monitors
    real-time progress.

    Args:
        config (RenderConfig): The rendering configuration object.
        logger (logging.Logger): The logger object to record logs.

    Returns:
        int: The number of frames per task (step). This value is used in post-processing.
    """
    total_frames = config.end - config.start + 1
    usable_workers = (get_usable_workers() if config.workers == 0
                     else min(config.workers, total_frames))
    step = config.per_task if config.per_task > 0 else max(1, usable_workers)

    tasks = create_tasks(
        config.comp_name, config.output_dir, config.start,
        config.end, step, config.ext, config.fpath,
        config.rs_template, config.om_template, config.verbose, logger
    )

    logger.info(job_info_msg(
        config.fpath, config.comp_name, config.rs_template,
        config.om_template, config.ext, config.verbose,
        config.start, config.end, step, step, config.output_dir
    ))

    with alive_bar(
        total_frames, spinner=None, title='PLEASE WAIT...',
        title_length=21, length=25, dual_line=True, stats=True,
        elapsed=True, manual=False, enrich_print=True,
        force_tty=True, refresh_secs=0.1
    ) as bar:

        bar.text = Msg.Dim(
            'INITIALIZING RENDER EXECUTION. PLEASE WAIT...', verbose=True
        )
        time.sleep(1)

        stop_event = Event()
        activate_system_monitor(bar, stop_event)
        progress_file_monitor(
            config.output_dir, config.ext, bar, total_frames,
            stop_event
        )

        with ProcessPoolExecutor(
            max_workers=usable_workers, initializer=worker_handler
        ) as executor:
            futures = {
                executor.submit(render_sequence, *task): task for task in tasks
            }
            for future in futures:
                try:
                    result = future.result()
                    logger.info(result)
                except Exception as e:
                    logger.error(f'RENDER ERROR: {e}')

        bar.title = 'PROCESS COMPLETED.'
        stop_event.set()

    return step


def finalize_rendering(
    config: RenderConfig, logger, step: int, start_time: datetime
):
    """
    ◦ Processes and reports the results after rendering is complete.

    This function handles the finalization stage of rendering. It consolidates
    split output files, validates for any frames with errors, summarizes the
    final rendering results for the user, and optionally initiates a preview
    of the output.

    Args:
        config (RenderConfig): The rendering configuration object.
        logger (logging.Logger): The logger object to record logs.
        step (int): The number of frames per task. Used for consolidating results.
        start_time (datetime): The start time of the overall rendering process.

    Returns:
        List[PathLike]: A list of paths to all successfully rendered image files.
    """
    logger.info('=' * 50)

    expected = get_output_paths(
        config.comp_name, config.output_dir, config.start,
        config.end, config.ext
    )

    result_images, errs = consolidate_outputs(
        config.output_dir, config.comp_name, config.start,
        config.end, step, config.ext, logger
    )
    invalids, invalids_log = get_invalid_images(
        config.output_dir, result_images, ext=config.ext
    )

    dafault_log_dir = remove_default_render_log(config.fpath, logger)    # ← REMOVE DEFALUT RENDER LOGs

    result, err_log = show_result(
        config.fpath, config.comp_name, expected, invalids, start_time
    )
    logger.info(render_info_msg(result_images, result, err_log + errs))

    print('-')
    message = (
        f'{len(invalids)} FILES INVALID. '
        f'CHECK THE DETAILED LIST IN "{invalids_log}"'
        if invalids else 'RENDER COMPLETED.'
    )
    Msg.Result(f'{message} (RESULT: {config.output_dir})', divide=False)
    Msg.Dim('FOR MORE DETAILS, CHECK THE LOG FILE IN THE RESULT DIR.')
    print('-')

    if config.preview:
        result_fnames = [os.path.basename(f) for f in result_images]
        preview_result(result_fnames, result_images)

    return result_images


def ae_render(config: RenderConfig) -> List[PathLike]:
    '''
    ◦ Executes an After Effects rendering sequence based on the provided configuration.

    Args:
        config (RenderConfig): A dataclass object containing all rendering settings:
            - fpath (PathLike): Path to the AE project file
            - comp_name (str): Composition name
            - output_dir (PathLike): Output directory
            - workers (int): Number of workers
            - start (int): Start frame
            - end (int): End frame
            - per_task (int): Number of frames per task
            - rs_template (str): Render Settings preset
            - om_template (str): Output Module preset
            - ext (str): File extension
            - verbose (str): Verbose flag
            - preview (bool): Preview result

    Returns:
        List[PathLike]: A list of paths to successfully rendered image files.

    Raises:
        None: Errors are logged and handled internally; returns an empty list on failure.

    Examples:
        config = RenderConfig(
            fpath='C:/tmp/test.aep',
            comp_name='test_comp',
            output_dir='C:/tmp',
            start=1,
            end=100,
            workers=4,
            per_task=0,
            rs_template='Multi-Machine Settings',
            om_template='YOUR_OUTPUT_MODULE_PRESET',
            ext='png',
            verbose='ERRORS_AND_PROGRESS',
            preview=False
        )
        ae_render(config)
    '''
    start_time = datetime.now()
    print('-')

    logger = setup_render(config)    # ← 1. RENDER.SETUP
    result_images = []

    try:
        step = execute_rendering(config, logger)    # ← 2. EXECUTE.RENDER
        result_images = finalize_rendering(config, logger, step, start_time)    # ← 3. FINALIZE.RENDER
    except (KeyboardInterrupt, SystemExit):
        msg = 'RENDERING INTERRUPTED BY USER.'
        logger.error(msg)
        Msg.Error(msg)
    except Exception as e:
        msg = f'UNEXPECTED ERROR: {e}'
        logger.error(msg)
        Msg.Error(msg)

    return result_images


def parse_arguments() -> RenderConfig:
    """
    Parses command-line (CLI) arguments provided when the script is executed.

    This function uses the argparse module to define all necessary arguments
    for the script (e.g., file path, composition name, frame range), reads
    the values entered by the user, and returns them as a RenderConfig object.

    Returns:
        RenderConfig: A RenderConfig object populated with settings entered by the user via the CLI.
    """
    parser = ArgumentParser(
        description='Python script for multicore After Effects rendering.'
    )
    parser.add_argument(
        '-f', '--fpath', required=True, help='PROJECT FILE PATH'
    )
    parser.add_argument(
        '-c', '--comp_name', required=True, help='COMPOSITION NAME'
    )
    parser.add_argument(
        '-o', '--output_dir', required=True, help='OUTPUT DIRECTORY'
    )
    parser.add_argument(
        '-s', '--start', type=int, required=True, help='START FRAME'
    )
    parser.add_argument(
        '-e', '--end', type=int, required=True, help='END FRAME'
    )
    parser.add_argument(
        '-w', '--workers', type=int, default=0,
        help='Number of worker processes (0 for auto-detect)'
    )
    parser.add_argument(
        '-t', '--per_task', type=int, default=0,
        help='Number of frames per task (0 for auto-detect)'
    )
    parser.add_argument(
        '-rst', '--rs_template', default='Multi-Machine Settings',
        help='Render Setting preset'
    )
    parser.add_argument(
        # SET YOUR OUTPUT MODULE PRESET
        '-omt', '--om_template', default='Multi-Machine Sequence',
        help='Output Module preset'
    )
    parser.add_argument(
        # THIS SHOULD MATCH THE FILE EXTENSION SPECIFIED IN YOUR OUTPUT MODULE PRESET.
        '-x', '--ext', default='png',
        help='File extension for output'
    )
    parser.add_argument(
        '-v', '--verbose', default='ERRORS_AND_PROGRESS',
        help='After Effects verbose flag'
    )
    parser.add_argument(
        '-p', '--preview', action='store_true',
        help='Preview result after rendering'
    )

    args = parser.parse_args()
    return RenderConfig(**vars(args))


def main():
    """
    Controls the main execution flow of the script.

    This function serves as the entry point of the program. It parses command-line
    arguments and calls the main rendering function (ae_render) based on the results.
    It also handles top-level exceptions that may occur during process execution.
    """
    try:
        config = parse_arguments()
        ae_render(config)
    except Exception as e:
        Msg.Error(f"Failed to start rendering: {e}")
        sys.exit(1)


if __name__ == '__main__':
    mp.set_start_method('spawn', force=True)
    main()