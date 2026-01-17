import sys

from scripts import load_json_data
from configs import Msg
from process.render_process_single import execute_render as execute_single
from process.render_process_multi import execute_render as execute_multi

def execute_render(json_path, logs=False, preview=False, logger=None):
    try:
        recipe_data = load_json_data(json_path)
        if not recipe_data:
            Msg.Error('Failed to load recipe data')
            if logger:
                logger.error('Failed to load recipe data')
            sys.exit(1)

        result_outputs = recipe_data.get('result_outputs', {})
        comp_count = len(result_outputs)

        if comp_count == 0:
            Msg.Error('No compositions found in recipe')
            if logger:
                logger.error('No compositions found in recipe')
            sys.exit(1)

        if comp_count == 1:
            if logger:
                logger.info(f'Selected single composition execution engine (1 composition)')
            exit_code, temp_dir = execute_single(json_path, logs, preview)
        else:
            if logger:
                logger.info(f'Selected multi composition execution engine ({comp_count} compositions)')
            exit_code, temp_dir = execute_multi(json_path, logs, preview)

        if exit_code != 0:
            Msg.Error('Rendering execution failed')
            if logger:
                logger.error('Rendering execution failed')
            sys.exit(1)

        return temp_dir

    except Exception as e:
        Msg.Error(f'Rendering execution error: {e}')
        if logger:
            logger.error(f'Rendering execution error: {e}')
        sys.exit(1)
