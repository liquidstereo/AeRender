
import os
import sys
import shutil
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.colorize import Msg
from configs.defaults import DEFAULT_TEMP_DIR
from configs.render_config import RenderConfig

from scripts._common import get_rel_path, trace_error, remove_exist
from scripts._ae_specifics import get_output_paths, remove_confirm
from scripts._process_kill import process_kill

def verify_aerender(logger=None):
    aerender_paths = ['aerender', 'aerender.exe']

    found_path = None
    for path in aerender_paths:
        if shutil.which(path) or os.path.exists(path):
            found_path = path
            break

    if not found_path:
        err_msg = (f'"aerender.exe" not found in system. '
                   f'Please install Adobe After Effects or add aerender to System PATH.')
        if logger:
            logger.error(err_msg)
        Msg.Error(err_msg)
        raise SystemExit(1)

    if logger:
        logger.info(f'Adobe After Effects aerender.exe successfully located in system PATH: {found_path}')

    return {'aerender_path': found_path, 'is_available': True}

def verify_file_exists(config, logger=None):
    if not config.fpath or not os.path.exists(config.fpath):
        return {'exists': False, 'error': f'File not found: {config.fpath}'}

    if not config.fpath.lower().endswith('.aep'):
        return {'exists': True, 'valid': False,
                'error': 'File must be .aep'}

    if logger:
        logger.info(f'File found: {os.path.basename(config.fpath)}')

    return {'exists': True, 'valid': True, 'path': config.fpath}

def verify_processes(logger=None):
    try:
        processes_terminated = process_kill('aerender', True, True)
        if logger and processes_terminated:
            logger.warning('Found running aerender.exe processes and successfully terminated them to prevent conflicts')
        return {'aerender_was_running': processes_terminated, 'terminated': processes_terminated}
    except Exception:
        return {'aerender_was_running': False, 'terminated': False}

def verify_results(config, logger=None):

    names = config.comp_name if isinstance(config.comp_name, list) else [config.comp_name]
    starts = config.start if isinstance(config.start, list) else [config.start]
    ends = config.end if isinstance(config.end, list) else [config.end]
    dirs = config.output_dir if isinstance(config.output_dir, list) else [config.output_dir]

    count = len(names)
    if len(starts) == 1 and count > 1:
        starts = starts * count
    if len(ends) == 1 and count > 1:
        ends = ends * count
    if len(dirs) == 1 and count > 1:
        dirs = dirs * count

    existing = []
    total = 0

    for i, name in enumerate(names):
        start = starts[i]
        end = ends[i]
        out_dir = dirs[i]

        files = get_output_paths(name, out_dir, start, end, config.ext)
        total += len(files)

        for path in files:
            if os.path.exists(path):
                existing.append(path)

    if len(existing) > 0:
        if logger:
            logger.warning(f'Found {len(existing)} existing files')

    return {
        'count': len(existing),
        'total': total,
        'files': existing,
        'has_existing': len(existing) > 0
    }

def confirm_execution(config: RenderConfig, logger=None):
    comp_names = config.comp_name if isinstance(config.comp_name, list) else [config.comp_name]
    is_multi = len(comp_names) > 1

    if not remove_confirm(config=config, comp_names=comp_names, is_multi=is_multi):
        if logger:
            logger.error('Process interrupted by user')
        Msg.Error('Process Interrupted By User.')
        sys.exit(0)

    exist_dirs = config.output_dir if isinstance(config.output_dir, list) else [config.output_dir]
    removed_dirs = []

    for d in exist_dirs:
        if os.path.exists(d):
            try:
                removed_dirs.append(d)
                logger.info(f'Remove Exist directories: {d}')
            except Exception:
                pass

def verify_temps(config, logger=None):
    tmps_dir = DEFAULT_TEMP_DIR

    if os.path.exists(tmps_dir):
        try:
            file_count = 0
            dir_count = 0
            for root, dirs, files in os.walk(tmps_dir):
                file_count += len(files)
                dir_count += len(dirs)

            err_msg = (f'Temporary dir. exists and must be deleted.\n'
                       f'Please delete the temporary dir. before proceeding:')

            if file_count > 0 or dir_count > 0:
                err_msg += f'{tmps_dir}, ({file_count} files, {dir_count} dirs)'

            if logger:
                logger.error(err_msg)

            Msg.Error(err_msg)
            raise SystemExit(1)

        except SystemExit:
            raise
        except Exception as e:
            err_msg = f'Error checking tmps directory: {trace_error(e)}'
            if logger:
                logger.error(err_msg)
            Msg.Error(err_msg)
            raise SystemExit(1)
    else:
        return {
            'exists': False,
            'path': tmps_dir,
            'files': 0,
            'dirs': 0,
            'needs_cleanup': False
        }

def verify_config(config: RenderConfig, logger=None):
    errors = []

    if not config.comp_name:
        errors.append('Composition name required')

    if isinstance(config.start, list) and isinstance(config.end, list):
        if len(config.start) != len(config.end):
            errors.append('Start/end lists length mismatch')
        for i, (start, end) in enumerate(zip(config.start, config.end)):
            if start >= end:
                errors.append(f'Invalid range comp {i}: {start}-{end}')
    else:
        if config.start >= config.end:
            errors.append(f'Invalid range: {config.start}-{config.end}')

    file_check = verify_file_exists(config, logger)
    if not file_check.get('valid', False):
        errors.append(file_check.get('error', 'Unknown file error'))

    if errors:
        msg = 'Config validation failed:\n' + '\n'.join(errors)
        if logger:
            logger.error(msg)
        Msg.Error(msg)
        raise SystemExit(1)

    comp_count = len(config.comp_name) if isinstance(config.comp_name, list) else 1
    if isinstance(config.start, list):
        frames = sum((end - start + 1)
                    for start, end in zip(config.start, config.end))
    else:
        frames = config.end - config.start + 1

    if logger:
        logger.info(f'Config valid: {comp_count} comps, {frames} frames')

    return {
        'valid': True,
        'comp_count': comp_count,
        'total_frames': frames,
        'file_check': file_check
    }

def render_preflight(config: RenderConfig, logger=None):

    start_time = time.time()

    try:
        aerender_info = verify_aerender(logger)

        aerender_status = verify_processes(logger)

        config_check = verify_config(config, logger)

        existing_results = verify_results(config, logger)

        if existing_results['has_existing']:
            confirm_execution(config, logger)

        tmps_status = verify_temps(config, logger)

        end_time = time.time()
        elapsed = round(end_time - start_time, 3)

        result = {
            'aerender_info': aerender_info,
            'aerender_status': aerender_status,
            'config_check': config_check,
            'existing_results': existing_results,
            'tmps_status': tmps_status,
            'time': elapsed,
            'passed': True
        }

        if logger:
            from scripts import format_elapsed_time
            elapsed_str = format_elapsed_time(elapsed)
            logger.info(f'All verifications completed, elapsed: {elapsed_str}')

        return result

    except Exception as e:
        end_time = time.time()
        elapsed = round(end_time - start_time, 3)
        msg = f'Init verification failed after {elapsed}s: {trace_error(e)}'
        Msg.Error(msg)
        if logger:
            logger.error(msg)
        sys.exit(1)

def main():
    import sys
    from process.main_parser import parse_arguments

    try:
        config = parse_arguments()
        result = render_preflight(config)

        if result['passed']:
            msg = (f'All verifications passed. (Elapsed: {result["time"]}, '
                   f'Comps: {result["config_check"]["comp_count"]}, '
                   f'Frames: {result["config_check"]["total_frames"]})'
                   )
            Msg.Dim(msg)
        else:
            Msg.Error('Verification failed')

    except Exception as e:
        Msg.Error(e)
        sys.exit(1)

if __name__ == '__main__':
    main()
