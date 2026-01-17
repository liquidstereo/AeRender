
import os
import sys
import time
import glob
import shutil
import datetime
from os import PathLike
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.colorize import Msg
from configs.defaults import DEFAULT_TEMP_DIR, DEFAULT_JSON_DIR, DEFAULT_LOG_DIR
from scripts._common import abs_path, trace_error

def log_cleanup(action: str, target: str, success: bool,
                logger=None, log_to_file: Optional[str] = None):
    status = 'SUCCESS' if success else 'FAILED'
    message = f'CLEANUP_{action}: {target} - {status}'

    if logger:
        if success:
            logger.info(message, show_func_info=True)
        else:
            logger.error(message, show_func_info=True)
    elif log_to_file:
        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(log_to_file, 'a', encoding='utf-8') as f:
                f.write(f'[{timestamp}] {message}\n')
        except Exception:
            pass
    else:
        if success:
            logger.info(message)
        else:
            logger.error(message)

def remove_empty_dir(dir_path: PathLike, logger=None) -> bool:
    dir_abs_path = abs_path(dir_path)

    try:
        if not os.path.exists(dir_abs_path):
            return True

        if not os.path.isdir(dir_abs_path):
            return False

        if not os.listdir(dir_abs_path):
            os.rmdir(dir_abs_path)
            log_cleanup('DELETE_EMPTY_DIR', dir_abs_path, True, logger)
            if logger:
                logger.info(f'Empty directory removed: {dir_abs_path}',
                           show_func_info=True)
            return True
        else:
            return False

    except Exception as e:
        log_cleanup('DELETE_EMPTY_DIR', dir_abs_path, False, logger)
        if logger:
            logger.error(f'Failed to remove empty directory {dir_abs_path}: '
                       f'{trace_error(e)}', show_func_info=True)
        return False

def clean_temps(temp_dir: PathLike = DEFAULT_TEMP_DIR,
                timeout: float = 5.0, logger=None) -> bool:
    temps_path = abs_path(temp_dir)

    if not os.path.exists(temps_path):
        if logger:
            logger.info(f'temps directory does not exist: {temps_path}',
                       show_func_info=True)
        return True

    if logger:
        logger.info(f'Starting temps directory cleanup: {temps_path}',
                   show_func_info=True)

    start_time = time.time()

    while os.path.exists(temps_path):
        try:
            shutil.rmtree(temps_path, ignore_errors=True)

            time.sleep(0.1)

            if time.time() - start_time > timeout:
                break

        except Exception as e:
            if logger:
                logger.error(f'Error during temps cleanup: {trace_error(e)}',
                           show_func_info=True)
            break

    success = not os.path.exists(temps_path)

    log_cleanup('DELETE_TEMPS', temps_path, success, logger)

    if success:
        if logger:
            logger.info(f'temps directory successfully cleaned: {temps_path}',
                       show_func_info=True)
        return True
    else:
        error_msg = f'temps directory cleanup timeout: {temps_path}'
        if logger:
            logger.error(error_msg, show_func_info=True)
        else:
            Msg.Error(error_msg)
        return False

def force_clean_temps(temp_dir: PathLike = DEFAULT_TEMP_DIR) -> bool:
    temps_path = abs_path(temp_dir)

    if not os.path.exists(temps_path):
        return True

    try:
        shutil.rmtree(temps_path, ignore_errors=True)
        success = not os.path.exists(temps_path)
        log_cleanup('FORCE_DELETE_TEMPS', temps_path, success)
        return success
    except Exception:
        log_cleanup('FORCE_DELETE_TEMPS', temps_path, False)
        return False

def clean_json(json_path: Optional[PathLike] = None,
               json_dir: PathLike = DEFAULT_JSON_DIR,
               pattern: str = '*.json', logger=None) -> int:
    deleted_count = 0

    if json_path:
        json_abs_path = abs_path(json_path)
        if os.path.exists(json_abs_path):
            try:
                os.remove(json_abs_path)
                deleted_count += 1
                log_cleanup('DELETE_JSON', json_abs_path, True, logger)
                if logger:
                    logger.info(f'JSON file deleted: {json_abs_path}',
                               show_func_info=True)
            except Exception as e:
                log_cleanup('DELETE_JSON', json_abs_path, False, logger)
                if logger:
                    logger.error(f'Failed to delete JSON file {json_abs_path}: '
                               f'{trace_error(e)}', show_func_info=True)
    else:
        json_dir_path = abs_path(json_dir)
        if os.path.exists(json_dir_path):
            search_pattern = os.path.join(json_dir_path, pattern)
            json_files = glob.glob(search_pattern)

            for json_file in json_files:
                try:
                    os.remove(json_file)
                    deleted_count += 1
                    log_cleanup('DELETE_JSON', json_file, True, logger)
                    if logger:
                        logger.info(f'JSON file deleted: {json_file}',
                                   show_func_info=True)
                except Exception as e:
                    log_cleanup('DELETE_JSON', json_file, False, logger)
                    if logger:
                        logger.error(f'Failed to delete JSON file {json_file}: '
                                   f'{trace_error(e)}', show_func_info=True)

            remove_empty_dir(json_dir_path, logger)

    if json_path and deleted_count > 0:
        parent_dir = os.path.dirname(abs_path(json_path))
        remove_empty_dir(parent_dir, logger)

    if logger:
        logger.info(f'JSON cleanup completed. Deleted {deleted_count} files',
                   show_func_info=True)

    return deleted_count

def clean_logs(log_path: Optional[PathLike] = None,
               log_dir: Optional[PathLike] = None,
               pattern: str = '*.log', logger=None) -> int:
    deleted_count = 0

    if log_path:
        log_abs_path = abs_path(log_path)
        if os.path.exists(log_abs_path):
            try:
                os.remove(log_abs_path)
                deleted_count += 1
                log_cleanup('DELETE_LOG', log_abs_path, True)
                if logger:
                    logger.info(f'Log file deleted: {log_abs_path}',
                               show_func_info=True)
            except Exception as e:
                log_cleanup('DELETE_LOG', log_abs_path, False)
                if logger:
                    logger.error(f'Failed to delete log file {log_abs_path}: '
                               f'{trace_error(e)}', show_func_info=True)
    elif log_dir:
        log_dir_path = abs_path(log_dir)
        if os.path.exists(log_dir_path):
            search_pattern = os.path.join(log_dir_path, pattern)
            log_files = glob.glob(search_pattern)

            for log_file in log_files:
                try:
                    os.remove(log_file)
                    deleted_count += 1
                    log_cleanup('DELETE_LOG', log_file, True)
                    if logger:
                        logger.info(f'Log file deleted: {log_file}',
                                   show_func_info=True)
                except Exception as e:
                    log_cleanup('DELETE_LOG', log_file, False)
                    if logger:
                        logger.error(f'Failed to delete log file {log_file}: '
                                   f'{trace_error(e)}', show_func_info=True)

            remove_empty_dir(log_dir_path, logger)

    if log_path and deleted_count > 0:
        parent_dir = os.path.dirname(abs_path(log_path))
        remove_empty_dir(parent_dir, logger)

    if logger:
        logger.info(f'Log cleanup completed. Deleted {deleted_count} files',
                   show_func_info=True)

    return deleted_count

def cleanup_all(json_path: Optional[PathLike] = None,
               temp_dir: PathLike = DEFAULT_TEMP_DIR,
               cleanup_json: bool = True,
               cleanup_logs: bool = True,
               cleanup_temps: bool = True,
               logger=None) -> dict:
    results = {
        'temps_cleaned': False,
        'json_deleted': 0,
        'logs_deleted': 0,
        'total_operations': 0
    }

    if logger:
        logger.info('Starting complete cleanup process', show_func_info=True)

    if cleanup_temps:
        results['temps_cleaned'] = clean_temps(temp_dir, logger=logger)
        results['total_operations'] += 1

    if cleanup_json:
        results['json_deleted'] = clean_json(json_path, logger=logger)
        results['total_operations'] += 1

    if cleanup_logs and json_path:
        try:
            from scripts._ae_specifics import load_json_data
            recipe_data = load_json_data(json_path)
            rendering_options = recipe_data.get('rendering_options', {})
            log_path = rendering_options.get('log_path')

            if log_path:
                results['logs_deleted'] = clean_logs(log_path, logger=logger)
                results['total_operations'] += 1
        except Exception as e:
            if logger:
                logger.error(f'Failed to extract log path from JSON: '
                           f'{trace_error(e)}', show_func_info=True)

    if logger:
        logger.info(f'Cleanup completed. Results: {results}',
                   show_func_info=True)

    return results

def cleanup_handler(cfg, json_path: str, logger):
    complete_info_data = None

    if not json_path:
        return complete_info_data

    try:
        try:
            from scripts._ae_specifics import load_json_data
            from .render_info import extract_json_data

            json_data = load_json_data(json_path)
            complete_info_data = extract_json_data(json_data)
            complete_info_data['json_path'] = json_path

        except Exception as e:
            if logger:
                logger.warning(f'Failed to extract completion info: {e}')

        cleanup_json = not getattr(cfg, 'save_json', False)
        cleanup_logs = False
        cleanup_temps = True

        if logger:
            logger.info('Starting post-render cleanup process',
                       show_func_info=True)
            logger.info(f'Cleanup options - JSON: {cleanup_json}, '
                       f'Logs: {cleanup_logs}, temps: {cleanup_temps}',
                       show_func_info=True)

        results = cleanup_all(
            json_path=json_path,
            cleanup_json=cleanup_json,
            cleanup_logs=cleanup_logs,
            cleanup_temps=cleanup_temps,
            logger=logger
        )

        if logger:
            logger.info(f'Post-render cleanup completed: {results}',
                       show_func_info=True)

    except Exception as e:
        if logger:
            logger.error(f'Cleanup error: {e}', show_func_info=True)
        else:
            Msg.Error(f'Cleanup error: {e}')
        force_clean_temps()

    return complete_info_data

def main():
    import argparse

    parser = argparse.ArgumentParser(description='AeRender cleanup utility')
    parser.add_argument('--all', action='store_true', help='Clean all')
    parser.add_argument('--temps', action='store_true', help='Clean temps')
    parser.add_argument('--json', type=str, help='Clean JSON files')
    parser.add_argument('--logs', type=str, help='Clean log files')

    args = parser.parse_args()

    if args.all:
        cleanup_all(cleanup_json=True, cleanup_logs=True, cleanup_temps=True)
    elif args.temps:
        clean_temps()
    elif args.json:
        clean_json(args.json if args.json != 'all' else None)
    elif args.logs:
        clean_logs(args.logs if args.logs != 'all' else None)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
