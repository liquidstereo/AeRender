import os, sys, time, re, math
from os import PathLike
from alive_progress import alive_bar
from concurrent.futures import ProcessPoolExecutor, as_completed

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from configs import Msg, DEFAULT_TEMP_DIR, PID_LOG_FILENAME
from scripts._common import trace_error, flush_lines, abs_path
from scripts._get_usable_workers import get_usable_workers

def is_invalid_image(fpath: PathLike, min_size: int, enhanced: bool = False) -> tuple[bool, list[PathLike]]:
    reasons = []

    if not os.path.exists(fpath):
        reasons.append('file not found')
        return True, reasons

    try:
        file_size = os.path.getsize(fpath)
        if file_size == 0:
            reasons.append('empty file')
            return True, reasons
        elif file_size < min_size:
            reasons.append(f'size too small ({file_size} bytes)')
    except OSError as e:
        reasons.append(f'file size error: {e}')
        return True, reasons

    try:
        img = cv2.imread(fpath, cv2.IMREAD_UNCHANGED)
        if img is None:
            reasons.append('unidentified image format')
            return True, reasons
    except Exception as e:
        reasons.append(f'image verification failed: {trace_error(e)}')
        return True, reasons

    if enhanced and img is not None:
        try:
            height, width = img.shape[:2]
            if width <= 0 or height <= 0:
                reasons.append(f'invalid dimensions: {width}x{height}')
            elif width < 10 or height < 10:
                reasons.append(f'suspicious dimensions: {width}x{height}')

            if width > 2 and height > 2:
                try:
                    center_pixel = img[height // 2, width // 2]
                except Exception:
                    reasons.append('corrupted pixel data')
        except Exception as e:
            reasons.append(f'advanced verification failed: {trace_error(e)}')

    return bool(reasons), reasons

def detect_rendering_artifacts(fpath: PathLike) -> list[str]:
    errors = []

    if not CV2_AVAILABLE:
        errors.append('OpenCV not available - enhanced verification disabled')
        return errors

    try:

        img_bgr = cv2.imread(fpath, cv2.IMREAD_COLOR)
        if img_bgr is None:
            errors.append('opencv cannot read image (BGR)')
            return errors

        img_unchanged = cv2.imread(fpath, cv2.IMREAD_UNCHANGED)
        if img_unchanged is None:
            errors.append('opencv cannot read image (unchanged)')
        elif img_unchanged.size == 0:
            errors.append('empty image data detected')

        height, width = img_bgr.shape[:2]

        if width <= 0 or height <= 0:
            errors.append(f'invalid dimensions: {width}x{height}')
        elif width > 100000 or height > 100000:
            errors.append(f'unrealistic dimensions: {width}x{height}')
        elif width * height < 64:
            errors.append(f'too small resolution: {width}x{height}')

        if width > 0 and height > 0:
            aspect_ratio = width / height
            if aspect_ratio > 20 or aspect_ratio < 0.05:
                errors.append(f'extreme aspect ratio: {aspect_ratio:.3f}')

        if len(img_bgr.shape) == 3:
            channels = img_bgr.shape[2]
            if channels not in [1, 3, 4]:
                errors.append(f'unusual channel count: {channels}')

        if img_unchanged is not None and len(img_unchanged.shape) >= 2:
            unchanged_channels = img_unchanged.shape[2] if len(img_unchanged.shape) == 3 else 1
            if channels != unchanged_channels and unchanged_channels not in [1, 3, 4]:
                errors.append(f'channel count mismatch: BGR={channels}, unchanged={unchanged_channels}')

        file_ext = os.path.splitext(fpath)[1].lower()

        if file_ext == '.png':
            if img_unchanged is not None and len(img_unchanged.shape) == 3:
                if img_unchanged.shape[2] not in [3, 4]:
                    errors.append(f'unusual PNG channel count: {img_unchanged.shape[2]}')

        elif file_ext in ['.jpg', '.jpeg']:
            if img_unchanged is not None and len(img_unchanged.shape) == 3:
                if img_unchanged.shape[2] != 3:
                    errors.append(f'JPEG should have 3 channels, got {img_unchanged.shape[2]}')

        if img_bgr.dtype not in [np.uint8, np.uint16, np.float32]:
            errors.append(f'unusual data type: {img_bgr.dtype}')

        try:
            corner_pixels = [
                img_bgr[0, 0],
                img_bgr[0, width-1],
                img_bgr[height-1, 0],
                img_bgr[height-1, width-1]
            ]
        except Exception:
            errors.append('corrupted pixel data access')

    except Exception as e:
        errors.append(f'opencv verification failed: {trace_error(e)[:100]}')

    return errors

def is_invalid_image_enhanced(fpath: PathLike, min_size: int,
                               check_artifacts: bool = True) -> tuple:
    is_invalid, basic_reasons = is_invalid_image(fpath, min_size, enhanced=False)

    if is_invalid:
        return is_invalid, basic_reasons

    all_reasons = basic_reasons[:]
    if check_artifacts:
        artifacts = detect_rendering_artifacts(fpath)
        all_reasons.extend(artifacts)

    return bool(all_reasons), all_reasons

def _validate_image_chunk(file_chunk: list[PathLike], min_size: int,
                          enhanced: bool = False) -> list[tuple]:
    invalid_files = []
    for fpath in file_chunk:
        try:
            if enhanced:
                is_invalid, reasons = is_invalid_image_enhanced(fpath, min_size, check_artifacts=True)
            else:
                is_invalid, reasons = is_invalid_image(fpath, min_size, enhanced=False)

            if is_invalid:
                invalid_files.append((fpath, reasons))
        except Exception as e:
            invalid_files.append((fpath, [f'validation error: {trace_error(e)}']))

    return invalid_files

def extract_frame_number(filepath: PathLike) -> int:
    filename = os.path.basename(filepath)
    numbers = re.findall(r'\d+', filename)
    if numbers:
        return int(numbers[-1])
    return -1

def detect_frame_drops(files: list[PathLike], start_frame: int = None, end_frame: int = None) -> list[int]:
    if not files:
        return []

    frame_numbers = []
    for file_path in files:
        if os.path.exists(file_path):
            frame_num = extract_frame_number(file_path)
            if frame_num != -1:
                frame_numbers.append(frame_num)

    if not frame_numbers:
        return []

    frame_numbers.sort()

    if start_frame is None:
        start_frame = min(frame_numbers)
    if end_frame is None:
        end_frame = max(frame_numbers)

    actual_frames = set(frame_numbers)

    missing_frames = []
    if end_frame - start_frame > 10000:
        chunk_size = 1000
        for chunk_start in range(start_frame, end_frame + 1, chunk_size):
            chunk_end = min(chunk_start + chunk_size - 1, end_frame)
            chunk_expected = set(range(chunk_start, chunk_end + 1))
            chunk_actual = actual_frames & chunk_expected
            chunk_missing = chunk_expected - chunk_actual
            missing_frames.extend(sorted(chunk_missing))
    else:
        expected_frames = set(range(start_frame, end_frame + 1))
        missing_frames = sorted(expected_frames - actual_frames)

    return missing_frames

def _process_with_progress_parallel(files: list[PathLike], min_size: int,
                                     enhanced: bool = False) -> list[tuple]:
    if len(files) < 50:
        return _process_with_progress_sequential(files, min_size, enhanced)

    num_workers = min(get_usable_workers(), len(files) // 10 + 1)

    chunk_size = math.ceil(len(files) / num_workers)
    file_chunks = [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]

    invalid_files = []
    completed_chunks = 0

    try:
        with alive_bar(len(files), title='PROCESSING⋯', dual_line=True,
                       stats=True, enrich_print=True) as bar:

                with ProcessPoolExecutor(max_workers=num_workers) as executor:
                    future_to_chunk = {
                        executor.submit(_validate_image_chunk, chunk, min_size, enhanced): chunk
                        for chunk in file_chunks
                    }

                    for future in as_completed(future_to_chunk):
                        chunk = future_to_chunk[future]
                        try:
                            chunk_invalids = future.result()
                            invalid_files.extend(chunk_invalids)
                            completed_chunks += 1

                            completed_files = completed_chunks * chunk_size
                            processed_files = min(completed_files, len(files))
                            bar.current = processed_files

                            error_count = len(invalid_files)
                            bar_text = f'PARALLEL CHECK: [{completed_chunks:02d}/{len(file_chunks):02d}] chunks'
                            if error_count:
                                bar_text += f' | {error_count} ERROR(s)'
                            bar.text = Msg.Dim(bar_text, verbose=True)

                        except Exception as e:
                            Msg.Yellow(f'Error processing chunk: {trace_error(e)}')

                bar.current = len(files)
                bar.title = 'PARALLEL PROCESS COMPLETED'

    except KeyboardInterrupt:
        time.sleep(0.1)
        raise
    except Exception as e:
        time.sleep(0.1)
        raise

    return invalid_files

def _process_with_progress_sequential(files: list[PathLike], min_size: int,
                                       enhanced: bool = False) -> list[tuple]:
    invalid_files = []
    error_count = 0

    try:
        with alive_bar(len(files), title='PROCESSING⋯', dual_line=True,
                       stats=True, enrich_print=True) as bar:
                for fpath in files:
                    fname = os.path.basename(fpath)

                    if enhanced:
                        is_invalid, reasons = is_invalid_image_enhanced(fpath, min_size, check_artifacts=True)
                    else:
                        is_invalid, reasons = is_invalid_image(fpath, min_size, enhanced=False)

                    if is_invalid:
                        invalid_files.append((fpath, reasons))
                        error_count += 1

                    bar_text = f'CHECKED: {fname}'
                    if error_count:
                        bar_text += f' {error_count} ERROR(s)'
                    bar.text = Msg.Dim(bar_text, verbose=True)
                    bar()

                bar.title = 'PROCESS COMPLETED'

    except KeyboardInterrupt:
        time.sleep(0.1)
        raise
    except Exception as e:
        time.sleep(0.1)
        raise

    return invalid_files

def image_verify(files: list[PathLike], min_size: int,
                 enhanced: bool = False) -> list[tuple]:
    if len(files) >= 100:
        num_workers = min(get_usable_workers(), len(files) // 20 + 1)
        chunk_size = math.ceil(len(files) / num_workers)
        file_chunks = [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]

        invalid_files = []

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(_validate_image_chunk, chunk, min_size, enhanced) for chunk in file_chunks]

            for i, future in enumerate(futures):
                try:
                    chunk_invalids = future.result()
                    invalid_files.extend(chunk_invalids)
                    Msg.Dim(f'CHUNK [{i+1:02d}/{len(futures):02d}] COMPLETED', flush=True)
                except Exception as e:
                    Msg.Error(f'Error in chunk [{i+1:02d}]: {trace_error(e)}')

        if invalid_files:
            Msg.Error(f'Verification Completed: {len(invalid_files)} Invalid images Found.')

    else:
        invalid_files = []

        for i, fpath in enumerate(files, 1):
            fname = os.path.basename(fpath)

            if enhanced:
                is_invalid, reasons = is_invalid_image_enhanced(fpath, min_size, check_artifacts=True)
            else:
                is_invalid, reasons = is_invalid_image(fpath, min_size, enhanced=False)

            if is_invalid:
                invalid_files.append((fpath, reasons))

            if i % 10 == 0 or i == len(files):
                Msg.Dim(f'Verifying rendered Images: [{i:02d}/{len(files):02d}] ({len(invalid_files)} Errors)', flush=True)

    return invalid_files

def get_invalid_images(dpath: PathLike, files: list[PathLike], ext: str,
                       min_file_size: int = 1024,
                       start_frame: int = None,
                       end_frame: int = None,
                       enhanced_check: bool = False,
                       comp_index: int = None,
                       total_comps: int = None,
                       logger=None) -> tuple:
    dpath = os.path.realpath(dpath).replace(os.sep, '/')

    verify_msg = 'Verifying rendered images… '
    verify_msg_surfux = 'Please wait…'

    if comp_index is not None and total_comps is not None:
        is_multi = True
        verify_msg_sequence = f'[{comp_index+1:02d}/{total_comps:02d}] '
    else:
        is_multi = False
        verify_msg_sequence = ''

    if is_multi:
        veryfy_ready_msg = f'{verify_msg}{verify_msg_sequence}{verify_msg_surfux}'
    else:
        veryfy_ready_msg = f'{verify_msg}{verify_msg_surfux}'

    Msg.Dim(f'{veryfy_ready_msg}', flush=True)

    if not files:
        err_msg = (f'Failed To Find \"{ext}\" '
                   f'Files In \"{dpath}\" for Verifying. ')
        Msg.Error(err_msg)
        return [], []

    invalid_files = image_verify(files, min_file_size, enhanced_check)

    Msg.Dim('Checking For Frame Drops…', verbose=True)
    dropped_frames = detect_frame_drops(files, start_frame, end_frame)

    if dropped_frames:
        drop_msg = f'Detected {len(dropped_frames)} Frame Drop(S): '
        drop_msg += f'{dropped_frames[:10]}{"…" if len(dropped_frames) > 10 else ""}'
        Msg.Error(drop_msg)

    has_issues = bool(invalid_files or dropped_frames)
    if has_issues:
        if logger:
            if invalid_files:
                logger.error('=== INVALID/CORRUPTED FILES ===')
                for fpath, reasons in invalid_files:
                    logger.error(f'{fpath} → {", ".join(reasons)}')

            if dropped_frames:
                logger.error('=== FRAME DROPS ===')
                logger.error(f'Missing frames: {", ".join(map(str, dropped_frames))}')
                logger.error(f'Total dropped frames: {len(dropped_frames)}')

        error_messages = []
        if invalid_files:
            error_messages.append(f'{len(invalid_files)} Invalid {ext.upper()} Files')
        if dropped_frames:
            error_messages.append(f'{len(dropped_frames)} Frame Drops')

        combined_message = ' AND '.join(error_messages)
        Msg.Red(f'{combined_message} Found.')

    else:
        verify_msg_surfux = '. Done.'

        if is_multi:
            Msg.Green(f'{verify_msg}{verify_msg_sequence}{verify_msg_surfux}',
                      flush=True)
            flush_lines(1)
        else:
            Msg.Green(f'{verify_msg}{verify_msg_surfux}', flush=True)
            flush_lines(1)

        flush_lines(1)

    sig_handler_log_path = abs_path(os.path.join(DEFAULT_TEMP_DIR, PID_LOG_FILENAME))
    if os.path.exists(sig_handler_log_path):
        try:
            os.remove(sig_handler_log_path)
        except OSError:
            pass

    return invalid_files, dropped_frames

if __name__ == '__main__':
    get_invalid_images(r'__IMGs_DIR__', [], 'png')
