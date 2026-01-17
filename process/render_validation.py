
import json
import os
import sys
import shutil
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs import Msg, DEFAULT_TEMP_DIR
from scripts import trace_error, make_dir
from .render_cleanup import clean_temps
from scripts._get_invalid_images import get_invalid_images
from scripts._ae_specifics import load_json_data
from scripts._common import flush_lines

def get_optimal_workers(json_path: str) -> int:
    return load_json_data(json_path, 'worker_configuration', 'configured_workers', 4)

def validate_chunk(chunk_data):
    files, idx, comp, comp_idx, total = chunk_data
    if not files:
        return [], []

    try:
        invalid_imgs, dropped = get_invalid_images(
            dpath=os.path.dirname(files[0]),
            files=files,
            ext='png',
            min_file_size=1024,
            enhanced_check=True,
            comp_index=comp_idx,
            total_comps=total
        )

        invalid = [fpath for fpath, reasons in invalid_imgs]
        valid = [f for f in files if f not in invalid]

        return valid, invalid

    except Exception:
        return [], files

def move_file(file_pair):
    src, dst = file_pair
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        return {'success': True, 'src': src, 'dst': dst}
    except Exception as e:
        return {'success': False, 'src': src, 'error': str(e)}

def check_rendered_status(comp_name: str, comp_data: Dict,
                          logger=None) -> Tuple[List[str], int]:

    frames = comp_data.get('frames', {})
    if not frames:
        err = f'No frames data found for {comp_name}'
        if logger:
            logger.error(err)
        Msg.Error(err)
        return [], 0

    rendered = []
    for frame_id, frame in frames.items():
        if frame.get('rendered', False):
            rendered.append(frame_id)

    total = len(frames)
    return rendered, total

def verify_temp_files(comp_name: str, comp_data: Dict,
                       rendered: List[str],
                       logger=None) -> Tuple[List[str], List[str]]:

    frames = comp_data.get('frames', {})
    existing = []
    dropped = []

    for frame_id in rendered:
        frame = frames.get(frame_id, {})
        tmp = frame.get('tmp', '')

        if not tmp:
            dropped.append(f'f{int(frame_id):04d}')
            continue

        if os.path.exists(tmp):
            existing.append(tmp)
        else:
            dropped.append(f'f{int(frame_id):04d}')
            if logger:
                logger.warning(f'Dropped file: {tmp}')

    return existing, dropped

def write_logs(comp_name: str, invalid: List[str],
               dropped: List[str]) -> Tuple[str, str]:
    invalid_log = ''
    dropped_log = ''

    if invalid:
        invalid_log = f'{comp_name}_invalid_files.log'
        try:
            with open(invalid_log, 'w', encoding='utf-8') as f:
                f.write(f'# Invalid Files for {comp_name}\n')
                f.write(f'# Generated: {datetime.now()}\n\n')
                for file_path in invalid:
                    f.write(f'{file_path}\n')
        except Exception:
            invalid_log = ''

    if dropped:
        dropped_log = f'{comp_name}_dropped_files.log'
        try:
            with open(dropped_log, 'w', encoding='utf-8') as f:
                f.write(f'# Dropped Files for {comp_name}\n')
                f.write(f'# Generated: {datetime.now()}\n\n')
                for frame_id in dropped:
                    f.write(f'{frame_id}\n')
        except Exception:
            dropped_log = ''

    return invalid_log, dropped_log

def validate_chunks(temp_files: List[str], comp_name: str,
                   workers: int, comp_index: int = None,
                   total_comps: int = None) -> Tuple[List[str], List[str]]:
    if not temp_files:
        return [], []

    chunk_size = max(10, len(temp_files) // workers)
    file_chunks = [temp_files[i:i+chunk_size]
                   for i in range(0, len(temp_files), chunk_size)]

    with ProcessPoolExecutor(max_workers=workers) as executor:
        chunk_data = [(chunk, i, comp_name, comp_index, total_comps) for i, chunk in enumerate(file_chunks)]
        chunk_results = list(executor.map(validate_chunk, chunk_data))

    all_valid = []
    all_invalid = []
    for valid_files, invalid_files in chunk_results:
        all_valid.extend(valid_files)
        all_invalid.extend(invalid_files)

    return all_valid, all_invalid

def verify_image_status(comp_name: str, temp_files: List[str],
                        logger=None, json_path: str = None,
                        use_parallel: bool = None, comp_index: int = None,
                        total_comps: int = None) -> Tuple[List[str], List[str]]:

    if not temp_files:
        if logger:
            logger.warning(f'No temp files to verify for {comp_name}')
        return [], []

    if use_parallel is None:
        use_parallel = len(temp_files) >= 100

    if use_parallel and json_path:
        workers = get_optimal_workers(json_path)
        if logger:
            logger.info(f'{comp_name}: Parallel processing '
                       f'({len(temp_files)} files, {workers} workers)')
        return validate_chunks(temp_files, comp_name, workers, comp_index, total_comps)

    try:
        temp_dir = os.path.dirname(temp_files[0])

        invalid_imgs, dropped_files = get_invalid_images(
            dpath=temp_dir,
            files=temp_files,
            ext='png',
            min_file_size=1024,
            enhanced_check=True,
            comp_index=comp_index,
            total_comps=total_comps,
            logger=logger
        )

        invalid_paths = [fpath for fpath, reasons in invalid_imgs]
        valid_files = [f for f in temp_files if f not in invalid_paths]

        if logger and invalid_paths:
            logger.warning(f'{comp_name}: {len(invalid_paths)} invalid files found')

        return valid_files, invalid_paths

    except Exception as e:
        err_msg = f'Image status verification failed: {trace_error(e)}'
        if logger:
            logger.error(err_msg)
        Msg.Error(err_msg)
        return [], temp_files

def update_verified_status(json_path: str, comp_name: str,
                           valid: List[str], comp_data: Dict,
                           logger=None) -> List[str]:

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        frames = comp_data.get('frames', {})
        verified = []
        count = 0

        for valid_file in valid:
            for frame_id, frame in frames.items():
                if frame.get('tmp', '') == valid_file:
                    if comp_name in data.get('result_outputs', {}):
                        json_frames = data['result_outputs'][comp_name].get('frames', {})
                        if frame_id in json_frames:
                            json_frames[frame_id]['verified'] = True
                            verified.append(frame_id)
                            count += 1
                    break

        if count > 0:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return verified

    except Exception as e:
        err_msg = f'Failed to update verified status: {trace_error(e)}'
        if logger:
            logger.error(err_msg)
        Msg.Error(err_msg)
        return []

def move_parallel(file_pairs: List[Tuple[str, str]],
                 workers: int) -> List[Dict]:
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(move_file, file_pairs))

    return results

def move_files(comp_name: str, comp_data: Dict, verified: List[str],
               logger=None, json_path: str = None,
               use_parallel: bool = None) -> Tuple[List[str], List[str]]:

    frames = comp_data.get('frames', {})

    pairs = []
    invalid = []

    for frame_id in verified:
        frame = frames.get(frame_id, {})
        tmp = frame.get('tmp', '')
        result = frame.get('result', '')

        if not tmp or not result:
            invalid.append(f'f{int(frame_id):04d}')
            continue

        pairs.append((tmp, result))

    if not pairs:
        return [], invalid

    if use_parallel is None:
        use_parallel = len(pairs) >= 50

    if use_parallel and json_path:
        workers = get_optimal_workers(json_path)
        if logger:
            logger.info(f'{comp_name}: Parallel file movement '
                       f'({len(pairs)} files, {workers} workers)')

        results = move_parallel(pairs, workers)

        moved = [r['dst'] for r in results if r['success']]
        failed = [f'f{int(verified[i]):04d}'
                 for i, r in enumerate(results) if not r['success']]

        if logger and failed:
            logger.error(f'{comp_name}: {len(failed)} parallel moves failed')

        return moved, failed + invalid

    moved = []
    failed = invalid[:]

    for tmp, result in pairs:
        try:
            result_dir = os.path.dirname(result)
            make_dir(result_dir)
            shutil.move(tmp, result)
            moved.append(result)
        except Exception as e:
            frame_id = next((fid for fid in verified
                           if frames.get(fid, {}).get('result', '') == result),
                          '0')
            failed.append(f'f{int(frame_id):04d}')
            if logger:
                logger.error(f'Frame move failed: {trace_error(e)}')

    if logger and failed:
        logger.error(f'{comp_name}: {len(failed)} file moves failed')

    return moved, failed

def update_moved_status(json_path: str, comp_name: str,
                        moved: List[str], comp_data: Dict,
                        logger=None) -> int:

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        frames = comp_data.get('frames', {})
        count = 0

        for moved_file in moved:
            for frame_id, frame in frames.items():
                if frame.get('result', '') == moved_file:
                    if comp_name in data.get('result_outputs', {}):
                        json_frames = data['result_outputs'][comp_name].get('frames', {})
                        if frame_id in json_frames:
                            json_frames[frame_id]['moved'] = True
                            count += 1
                    break

        if count > 0:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return count

    except Exception as e:
        err_msg = f'Failed to update moved status: {trace_error(e)}'
        if logger:
            logger.error(err_msg)
        Msg.Error(err_msg)
        return 0

def validation_results(results: Dict[str, Any], logger=None, comp_info: str = '') -> Dict[str, Any]:

    total_compositions = results.get('total_compositions', 0)
    total_moved = results.get('total_moved', 0)
    total_expected = results.get('total_expected', 0)
    overall_success = results.get('overall_success', False)

    if logger:
        logger.info(f'Final: {total_moved}/{total_expected} files, '
                    f'success: {overall_success}')

    comp_results = results.get('composition_results', {})
    failed_comps = [name for name, result in comp_results.items()
                   if not result.get('success', False)]
    if failed_comps:
        Msg.Error(f'Failed: {", ".join(failed_comps)}')
        logger.error(f'Failed: {", ".join(failed_comps)}')

    return results

def verify_render_output(json_path: str, logger=None,
                         force_parallel: bool = False, temp_dir: str = None) -> Dict[str, Any]:
    start_time = datetime.now()

    if logger:
        logger.info(f'Starting validation: {os.path.basename(json_path)}')

    try:
        recipe_data = load_json_data(json_path, logger=logger)

        if temp_dir:
            tmps_dir = os.path.abspath(temp_dir)
        else:
            tmps_dir = DEFAULT_TEMP_DIR

        if not os.path.exists(tmps_dir):
            err_msg = f'tmps directory not found: {tmps_dir}'
            if logger:
                logger.error(err_msg)
            Msg.Error(err_msg)
            raise FileNotFoundError(err_msg)

        composition_results = {}
        total_moved = 0
        total_expected = 0
        all_success = True

        total_comps = len(recipe_data['result_outputs'])

        for comp_idx, (comp_name, comp_data) in enumerate(recipe_data['result_outputs'].items(), 1):

            comp_progress = f'Starting Validating {comp_name} [{comp_idx:02d}/{total_comps:02d}]'
            Msg.Dim(comp_progress, flush=True)

            try:
                Msg.Dim(f'{comp_progress} - Checking rendered status...', flush=True)
                rendered, total_frames = check_rendered_status(
                    comp_name, comp_data, logger)

                Msg.Dim(f'{comp_progress} - Verifying temp files...', flush=True)
                existing, dropped = verify_temp_files(
                    comp_name, comp_data, rendered, logger)

                Msg.Dim(f'{comp_progress} - Validating images...', flush=True)
                valid, invalid = verify_image_status(
                    comp_name, existing, logger, json_path,
                    use_parallel=force_parallel, comp_index=comp_idx-1,
                    total_comps=total_comps)

                Msg.Dim(f'{comp_progress} - Updating verified status...', flush=True)
                verified = update_verified_status(
                    json_path, comp_name, valid, comp_data, logger)

                Msg.Dim(f'{comp_progress} - Moving files...', flush=True)
                moved, failed = move_files(
                    comp_name, comp_data, verified, logger, json_path,
                    use_parallel=force_parallel)

                Msg.Dim(f'{comp_progress} - Updating moved status...', flush=True)
                count = update_moved_status(
                    json_path, comp_name, moved, comp_data, logger)

                frames = comp_data.get('frames', {})
                expected = []
                for frame_id in rendered:
                    frame = frames.get(frame_id, {})
                    result = frame.get('result', '')
                    if result:
                        expected.append(result)

                invalid_log, dropped_log = write_logs(
                    comp_name, invalid, dropped)

                comp_success = (len(failed) == 0 and
                               len(invalid) == 0 and
                               len(dropped) == 0)
                composition_results[comp_name] = {
                    'success': comp_success,
                    'total_frames': total_frames,
                    'rendered_frames': len(rendered),
                    'verified_files': len(valid),
                    'moved_files': len(moved),
                    'expected_files': expected,
                    'moved_file_paths': moved,
                    'failed_moves': failed,
                    'invalid_files': invalid,
                    'dropped_files': dropped,
                    'invalid_log': invalid_log,
                    'dropped_log': dropped_log
                }

                total_moved += len(moved)
                total_expected += len(rendered)

                comp_display_name = f'{comp_name} [{comp_idx:02d}/{total_comps:02d}]'
                if len(rendered) > 0:
                    success_rate = (len(moved) / len(rendered) * 100)
                    result_msg = f'{comp_display_name} - Validation completed: {len(moved)}/{len(rendered)} files ({success_rate:.1f}%)'

                    if comp_success:
                        Msg.Dim(result_msg, flush=True)
                    else:
                        Msg.Red(f'{result_msg}, Found Error.')

                if logger:
                    if comp_success:
                        logger.info(f'{comp_name}: Validated {len(moved)}/{total_frames} files')
                    else:
                        error_count = len(failed + invalid + dropped)
                        logger.warning(f'{comp_name}: Validated {len(moved)}/{total_frames} files, {error_count} errors')

                if not comp_success:
                    all_success = False

                errors = failed + invalid + dropped
                if errors:
                    err_msg = (f'{comp_name}: {len(failed)} move errors, '
                               f'{len(invalid)} invalid, '
                               f'{len(dropped)} dropped')
                    if logger:
                        logger.error(err_msg)
                    Msg.Error(err_msg, divide=False)

            except Exception as e:
                err_msg = (f'Composition {comp_name} processing failed: '
                             f'{trace_error(e)}')
                if logger:
                    logger.error(err_msg)
                Msg.Error(err_msg)

                composition_results[comp_name] = {
                    'success': False,
                    'error': err_msg,
                    'moved_files': 0,
                    'expected_files': 0
                }
                all_success = False

        cleanup_success = clean_temps(tmps_dir, timeout=5.0, logger=logger)
        if logger:
            status = 'completed' if cleanup_success else 'failed'
            logger.info(f'Cleanup: {status}')

        end_time = datetime.now()
        elapsed_time = end_time - start_time

        results = {
            'recipe_file': json_path,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'elapsed_time': str(elapsed_time),
            'overall_success': all_success and cleanup_success,
            'total_compositions': len(recipe_data['result_outputs']),
            'total_moved': total_moved,
            'total_expected': total_expected,
            'composition_results': composition_results,
            'temp_cleanup_success': cleanup_success,
            'summary': {
                'success_rate': f'{total_moved}/{total_expected}' if total_expected > 0 else '0/0',
                'elapsed_seconds': elapsed_time.total_seconds()
            }
        }

        if total_expected > 0:
            overall_success_rate = (total_moved / total_expected * 100)
            success_comps = sum(1 for r in composition_results.values() if r.get('success', False))

            summary_msg = (f'Render Results Verified. '
                           f'{total_moved}/{total_expected} files. ({overall_success_rate:.1f}%) '
                           f'{total_comps} compositions')
            if all_success and cleanup_success:
                Msg.Green(summary_msg)
            else:
                Msg.Red(f'{summary_msg}, Found Error.')

            if logger:
                detailed_summary = f'{summary_msg}, {elapsed_time.total_seconds():.1f}s'
                if all_success and cleanup_success:
                    logger.info(detailed_summary)
                else:
                    failed_comps = [name for name, result in composition_results.items()
                                   if not result.get('success', False)]
                    logger.warning(f'{detailed_summary}, cleanup: {"ok" if cleanup_success else "failed"}')
                    if failed_comps:
                        logger.error(f'Failed compositions: {", ".join(failed_comps)}')

        final_results = validation_results(results, logger)

        return final_results

    except Exception as e:
        err_msg = f'9-step orchestration failed: {trace_error(e)}'
        if logger:
            logger.error(err_msg)
        Msg.Error(err_msg)

        return {
            'recipe_file': json_path,
            'overall_success': False,
            'error': err_msg,
            'elapsed_time': str(datetime.now() - start_time)
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description='AeRender 렌더링 검증')
    parser.add_argument('json_path')
    parser.add_argument('-l', '--logs', action='store_true')
    args = parser.parse_args()

    logger = None
    if args.logs:
        from scripts import create_debug_logger
        logger = create_debug_logger('RenderValidation')

    try:
        results = verify_render_output(args.json_path, logger)
        exit(0 if results.get('overall_success') else 1)
    except Exception as e:
        Msg.Error(f'Failed: {trace_error(e)}')
        exit(1)

if __name__ == '__main__':
    main()
