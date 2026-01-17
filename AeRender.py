import sys
import multiprocessing as mp
import logging
import time

from configs import Msg

from scripts import setup_handler

from process import (
    parse_arguments,
    render_preflight,
    render_init,
    execute_render,
    verify_render_output,
    render_result,
    render_preview,
    logger_init,
    render_result_log,
    render_start_info,
    render_complete_info,
    cleanup_handler
)
from process.render_cleanup import force_clean_temps

def main():
    start_time = time.time()

    try:
        setup_handler(logging.getLogger(), None)
    except:
        setup_handler(None, None)

    try:
        cfg = parse_arguments()
        logger = logger_init(cfg, clear_existing=True)

        print('-')

        render_start_info(cfg, logger)

        render_preflight(cfg, logger)

        _, json_path = render_init(cfg, logger)
        print('-')

        works_dir = execute_render(json_path, cfg.logs, cfg.preview, logger)
        print('-')

        results = verify_render_output(json_path, logger=logger, temp_dir=works_dir)
        print('-')

        result_success, preview_data = render_result(json_path, results, cfg.logs, logger)
        render_result_log(json_path, logger)

        if cfg.preview:
            render_preview(preview_data, result_success)

        print('-')

        complete_info = cleanup_handler(cfg, json_path, logger)

        elapsed_time = time.time() - start_time
        render_complete_info(complete_info, results, elapsed_time, logger)

        print('-')

        sys.exit(0 if results.get('overall_success', False) else 1)

    except KeyboardInterrupt:
        Msg.Error('Process interrupted by user')
        force_clean_temps()
        sys.exit(1)
    except Exception as e:
        Msg.Error(f'Failed to start rendering: {e}')
        force_clean_temps()
        sys.exit(1)

if __name__ == '__main__':
    mp.set_start_method('spawn', force=True)
    main()
