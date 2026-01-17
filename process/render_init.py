
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.colorize import Msg
from configs.defaults import (
    DEFAULT_SYSTEM_USAGE, DEFAULT_OUTPUT_DIR, DEFAULT_JSON_DIR,
    DEFAULT_FILE_EXTENSION, DEFAULT_TEMP_DIR,
    TEMP_PROJECT_PREFIX, DEFAULT_FRAMES_PER_TASK
)
from configs.render_config import RenderConfig

from scripts._common import trace_error, make_dir, sanitize_string
from scripts._ae_specifics import get_output_paths, get_temp_name, is_multi_comp
from scripts._get_usable_workers import get_usable_workers

def generate_worker_config(config: RenderConfig, logger=None):
    if logger:
        logger.info('Starting worker configuration generation',
                   show_func_info=True)

    optimal_workers = get_usable_workers()
    configured_workers = config.get_calculated_workers()

    if config.per_task > 0:
        frames_per_task = config.per_task
    else:
        if isinstance(config.start, list):
            total_frames = sum((end - start + 1)
                             for start, end in zip(config.start, config.end))
        else:
            total_frames = config.end - config.start + 1

        frames_per_task = max(1, total_frames // (configured_workers * 2))

    if isinstance(config.start, list):
        estimated_tasks = 0
        for start, end in zip(config.start, config.end):
            comp_frames = end - start + 1
            comp_tasks = max(1, comp_frames // frames_per_task)
            estimated_tasks += comp_tasks
    else:
        total_frames = config.end - config.start + 1
        estimated_tasks = max(1, total_frames // frames_per_task)

    worker_config = {
        'optimal_workers': optimal_workers,
        'configured_workers': configured_workers,
        'frames_per_task': frames_per_task,
        'estimated_tasks': estimated_tasks,
        'system_usage_ratio': DEFAULT_SYSTEM_USAGE,
        'render_settings': {
            'rs_template': config.rs_template,
            'om_template': config.om_template,
            'verbose_level': config.verbose
        },
    }

    if logger:
        logger.info(f'Worker config generated: {configured_workers} workers, '
                   f'{frames_per_task} frames/task, {estimated_tasks} tasks',
                   show_func_info=True)

    return worker_config

def create_render_recipe_json(config: RenderConfig, worker_config: dict,
                              logger=None, output_dir: str = None):
    start_time = datetime.now()
    if logger:
        logger.info('Starting render recipe JSON generation',
                   show_func_info=True)

    if output_dir is None:
        if is_multi_comp(config=config):
            output_dir = DEFAULT_OUTPUT_DIR
        else:
            if isinstance(config.output_dir, list):
                output_dir = config.output_dir[0]
            else:
                output_dir = config.output_dir

    project_root = os.path.dirname(os.path.abspath(config.fpath))
    project_name = os.path.splitext(os.path.basename(config.fpath))[0]
    tmps_dir = DEFAULT_TEMP_DIR
    temp_project_path = os.path.join(tmps_dir,
                                   f'{TEMP_PROJECT_PREFIX}_'
                                   f'{os.path.basename(config.fpath)}')

    comp_names = (config.comp_name if isinstance(config.comp_name, list)
                 else [config.comp_name])
    starts = (config.start if isinstance(config.start, list)
              else [config.start])
    ends = (config.end if isinstance(config.end, list)
            else [config.end])
    output_dirs = (config.output_dir if isinstance(config.output_dir, list)
                  else [config.output_dir])

    num_comps = len(comp_names)
    if len(starts) == 1 and num_comps > 1:
        starts = starts * num_comps
    if len(ends) == 1 and num_comps > 1:
        ends = ends * num_comps
    if len(output_dirs) == 1 and num_comps > 1:
        output_dirs = output_dirs * num_comps

    recipe_data = {
        'recipe_info': {
            'created_timestamp': datetime.now().isoformat(),
            'aerender_version': '2.0',
            'project_name': project_name
        },
        'project_settings': {
            'project_file': config.fpath,
            'compositions': config.comp_name,
            'file_extension': config.ext,
            'render_settings_template': config.rs_template,
            'output_module_template': config.om_template,
            'verbose_level': (config.verbose if hasattr(config, 'verbose')
                             else 'ERRORS_AND_PROGRESS'),
            'temp_directory': tmps_dir,
            'temp_project': temp_project_path,
            'result_dir': [os.path.abspath(dir) for dir in output_dirs]
        },
        'worker_configuration': worker_config,
        'rendering_options': {
            'compositions': config.comp_name,
            'start_frames': config.start,
            'end_frames': config.end,
            'workers': worker_config['configured_workers'],
            'per_task': worker_config['frames_per_task'],
            'enable_preview': getattr(config, 'preview', False),
            'enable_logging': getattr(config, 'logs', False),
            'save_json': getattr(config, 'save_json', False)
        }
    }

    recipe_data['result_outputs'] = {}

    if logger:
        logger.info(f'Processing {len(comp_names)} compositions',
                   show_func_info=True)

    for i, comp_name in enumerate(comp_names):
        if logger:
            logger.info(f'Processing composition {i+1}/{len(comp_names)}: '
                       f'{comp_name}', show_func_info=True)
        start = starts[i]
        end = ends[i]
        comp_output_dir = output_dirs[i]

        expected_files = get_output_paths(comp_name, comp_output_dir,
                                        start, end, config.ext)

        frames_per_task = worker_config.get('frames_per_task',
                                          DEFAULT_FRAMES_PER_TASK)

        frame_map = {}
        chunk_tasks = []

        for chunk_start in range(start, end + 1, frames_per_task):
            chunk_end = min(chunk_start + frames_per_task - 1, end)

            chunk_dir_name = get_temp_name(comp_name, chunk_start,
                                          chunk_end)
            chunk_dir_path = os.path.join(tmps_dir, chunk_dir_name)
            result_comp_name = sanitize_string(comp_name)

            for frame_num in range(chunk_start, chunk_end + 1):
                temp_relative_frame = frame_num - chunk_start
                temp_file = os.path.join(chunk_dir_path,
                                        f"{result_comp_name}."
                                        f"{temp_relative_frame:04d}."
                                        f"{config.ext}")
                result_file = os.path.join(comp_output_dir,
                                         f"{result_comp_name}."
                                         f"{frame_num:04d}."
                                         f"{config.ext}")

                frame_map[frame_num] = {
                    'tmp': temp_file,
                    'result': result_file,
                    'rendered': False,
                    'moved': False,
                    'verified': False
                }

            output_pattern = os.path.join(chunk_dir_path,
                                        f"{result_comp_name}.[####]."
                                        f"{config.ext}")

            aerender_command = [
                "aerender",
                "-project", temp_project_path,
                "-comp", comp_name,
                "-RStemplate", config.rs_template,
                "-OMtemplate", config.om_template,
                "-output", output_pattern,
                "-s", str(chunk_start),
                "-e", str(chunk_end),
                "-v", config.verbose
            ]

            chunk_tasks.append({
                'chunk_id': f'{comp_name}_{chunk_start:04d}_'
                           f'{chunk_end:04d}',
                'temp_directory': chunk_dir_path,
                'file_count': chunk_end - chunk_start + 1,
                'aerender_command': aerender_command
            })

        recipe_data['result_outputs'][comp_name] = {
            'frames': frame_map,
            'workflow': {
                'temp_workspace': tmps_dir,
                'temp_project': os.path.join(tmps_dir,
                                             temp_project_path),
                'chunk_tasks': chunk_tasks
            },
            'output_dir': comp_output_dir,
            'total': end - start + 1,
            'completed': 0,
            'elapsed_time': '00:00:00'
        }

    project_name = sanitize_string(project_name, str)

    if len(comp_names) > 1:
        json_filename = f'{project_name}_Comps_info.json'
    else:
        comp_name = sanitize_string(comp_names[0], str)
        json_filename = f'{project_name}_{comp_name}_info.json'

    json_dir = os.path.join(project_root, DEFAULT_JSON_DIR)
    json_path = os.path.join(json_dir, json_filename)

    from configs.defaults import DEFAULT_LOG_DIR
    log_dir = DEFAULT_LOG_DIR

    if len(comp_names) > 1:
        log_filename = f'{project_name}_Comps.log'
    else:
        safe_comp_name = sanitize_string(comp_names[0], str)
        log_filename = f'{project_name}_{safe_comp_name}.log'

    log_path = os.path.join(log_dir, log_filename)

    recipe_data['rendering_options']['json_path'] = os.path.abspath(json_path)
    recipe_data['rendering_options']['log_path'] = os.path.abspath(log_path)

    try:
        if logger:
            logger.info(f'Creating JSON directory: {json_dir}',
                       show_func_info=True)
        make_dir(json_dir)

        if logger:
            logger.info(f'Saving render recipe to: {json_path}',
                       show_func_info=True)
            logger.info(f'Result directories: {output_dirs}',
                       show_func_info=True)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(recipe_data, f, indent=2, ensure_ascii=False)

        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()

        if logger:
            logger.info(f'Render recipe JSON successfully saved: '
                       f'{os.path.basename(json_path)} '
                       f'(Generated in {elapsed_time:.3f}s)',
                       show_func_info=True)

        return os.path.abspath(json_path)

    except Exception as e:
        error_msg = f'Failed to save render recipe: {trace_error(e)}'
        if logger:
            logger.error(error_msg, show_func_info=True)
        Msg.Error(error_msg)
        return None

def render_init(config: RenderConfig, logger=None):

    if logger:
        logger.info('Starting render task recipe generation process',
                   show_func_info=True)

    try:
        if logger:
            logger.info('Generating worker configuration',
                       show_func_info=True)
        worker_config = generate_worker_config(config, logger)

        if logger:
            logger.info('Creating render recipe JSON',
                       show_func_info=True)
        json_path = create_render_recipe_json(config, worker_config, logger)
        if logger:
            logger.info(f'Recipe JSON created: {json_path}',
                       show_func_info=True)

        return worker_config, json_path

    except Exception as e:
        error_msg = (f'Render task recipe generation failed: '
                     f'{trace_error(e)}')
        Msg.Error(error_msg)
        if logger:
            logger.error(error_msg)
        sys.exit(1)

def main():
    import sys
    from process.main_parser import parse_arguments

    try:
        config = parse_arguments()

        worker_config, json_path = render_init(config)

        if json_path:
            print(f"RECIPE: {json_path}")
            print(f"WORKERS: {worker_config['configured_workers']}")
            print(f"FRAMES/TASK: {worker_config['frames_per_task']}")
            print(f"ESTIMATED TASKS: {worker_config['estimated_tasks']}")
        else:
            print("ERROR: No JSON file created")

    except SystemExit as e:
        print(f"ERROR: {e}")
        sys.exit(e.code)
    except Exception as e:
        print(f"ERROR: {trace_error(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
