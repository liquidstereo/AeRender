
import os
import re
import json
from os import PathLike
from typing import Union, List, Dict, Any
import winreg

from configs import Msg, Logger
from scripts._common import abs_path, remove_exist, flush_lines, trace_error

def is_multi_comp(config=None, comp_name=None, total_comps=None) -> bool:
    if total_comps is not None:
        return total_comps > 1

    if comp_name is not None:
        return isinstance(comp_name, list)

    if config is not None:
        return isinstance(config.comp_name, list)

    return False

def parse_multi_values(value_str: str) -> list:
    if not value_str:
        return []

    if ',' in value_str:
        values = [v.strip() for v in value_str.split(',') if v.strip()]
    else:
        parts = [v.strip() for v in re.split(r'\s+', value_str.strip()) if v.strip()]
        if len(parts) > 1:
            try:
                for part in parts:
                    int(part)
                values = parts
            except ValueError:
                values = [value_str.strip()]
        else:
            values = parts

    return values

def has_multiple_values(value_str: str) -> bool:
    if not value_str or not isinstance(value_str, str):
        return False

    if ',' in value_str:
        return True

    parts = [p.strip() for p in re.split(r'\s+', value_str.strip()) if p.strip()]
    if len(parts) > 1:
        try:
            for part in parts:
                int(part)
            return True
        except ValueError:
            return False

    return False

def sanitize_names(comp: str, strict: bool = True) -> str:
    if strict:
        sanitized = re.sub(r'[/\\:\*\?"<>\|\s\[\](){}@#$%^&+=~`\';,\.\-]+', '_', comp)

        sanitized = re.sub(r'^_+|_+$', '', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
    else:
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', '_', comp)

        reserved_names = r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)'
        if re.match(reserved_names, sanitized, re.IGNORECASE):
            sanitized = f"_{sanitized}"

        sanitized = re.sub(r'_+', '_', sanitized)

        sanitized = re.sub(r'^_+|_+$', '', sanitized)

        if not sanitized.strip():
            sanitized = "Untitled"

    return sanitized

def remove_confirm(config=None, comp_names=None, is_multi=False) -> bool:

    existing_files = []

    if is_multi and comp_names:
        for i, comp_name in enumerate(comp_names):
            start = config.start[i] if isinstance(config.start, list) else config.start
            end = config.end[i] if isinstance(config.end, list) else config.end

            if isinstance(config.output_dir, list):
                comp_output_dir = config.output_dir[i]
            else:
                comp_output_dir = os.path.join(config.output_dir, comp_name)

            comp_output_paths = get_output_paths(comp_name, comp_output_dir, start, end, config.ext)
            existing_comp_files = [f for f in comp_output_paths if os.path.exists(f)]
            existing_files.extend(existing_comp_files)
    else:
        comp_name = config.comp_name if isinstance(config.comp_name, str) else config.comp_name[0]
        start = config.start if isinstance(config.start, int) else config.start[0]
        end = config.end if isinstance(config.end, int) else config.end[0]

        single_output_dir = config.output_dir[0] if isinstance(config.output_dir, list) else config.output_dir
        output_paths = get_output_paths(comp_name, single_output_dir, start, end, config.ext)
        existing_files = [f for f in output_paths if os.path.exists(f)]

    if not existing_files:
        return True

    existing_count = len(existing_files)
    if is_multi:
        comp_info = f'{len(comp_names)} compositions'
        multi_note = ''
    else:
        comp_info = f'\"{comp_name}\"'
        multi_note = ''

    print(f'-')

    prompt_header = (
        f'Warning: Found {existing_count} Existing Files '
        f'for {comp_info}{multi_note}.'
    )
    Msg.Red(prompt_header, plain=False)

    prompt_text = (
        f'To retain files, back up or change the output dir '
        f'and execute again.\n'
    )

    if is_multi:
        prompt_text += f'This decision applies to all {len(comp_names)} compositions.\n'

    prompt_text = Msg.Plain(prompt_text, verbose=True, plain=True)
    prompt_text += Msg.Red('All Existing Files Will Be Removed To Continue.\n', verbose=True)

    prompt_confirm = Msg.Cyan(f'Remove Existing Files? (Y/N): ', verbose=True)

    prompt = prompt_header + prompt_text + prompt_confirm
    prompt_count = len(prompt.splitlines()) + 3

    prompt_start = False
    try:
        while True:
            if not prompt_start:
                user_input = input(f'{prompt_text}{prompt_confirm}').lower().strip()
            else:
                user_input = input(f'{prompt_confirm}').lower().strip()

            if user_input == 'y':
                flush_lines(prompt_count)
                return True
            elif user_input == 'n':
                flush_lines(prompt_count)
                return False
            else:
                flush_lines(1)
                Msg.Dim('Not An Appropriate Choice. Please Enter "Y" Or "N"')
                prompt_count += 2
                prompt_start = True

    except KeyboardInterrupt:
        return False

def system_env_paths() -> List[str]:
    reg_path = (r'SYSTEM\CurrentControlSet\Control\Session Manager'
                r'\Environment')
    reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
    sys_env_paths = winreg.QueryValueEx(reg_key, 'Path')[0]
    return [p for p in sys_env_paths.split(';') if p]

def init_fpath(fpath: PathLike) -> bool:
    if not os.path.isfile(fpath):
        raise FileNotFoundError(f'NO SUCH FILE OR DIRECTORY: {fpath}')
    return True

def pre_execute(fpath: PathLike) -> bool:
    init_fpath(fpath)
    env_paths = system_env_paths()
    query_string = 'Adobe After Effects'
    query_result = list(filter(lambda c: query_string in c, env_paths))

    if not query_result:
        raise Exception(
            'Make Sure "aerender.Exe" Command Is Properly Set '
            'In The System\'s Path'
        )
    return True

def get_output_paths(comp: str, output_dir: str,
                     start: int, end: int, ext: str) -> List[PathLike]:
    sanitized_name = sanitize_names(comp)
    return [
        abs_path(os.path.join(output_dir, f'{sanitized_name}.{i:04d}.{ext}'))
        for i in range(start, end + 1)
    ]

def rename_files(src_dir: PathLike, dst_dir: PathLike,
                 files: List[str], comp: str,
                 start: int,
                 logger: Logger) -> tuple[List[str], List[str]]:
    moved, errors = [], []

    os.makedirs(dst_dir, exist_ok=True)

    sanitized_name = sanitize_names(comp)

    for i, fname in enumerate(files):
        src = os.path.join(src_dir, fname)
        ext = fname.split('.')[-1]
        dst = os.path.join(dst_dir, f'{sanitized_name}.{start + i:04d}.{ext}')
        dst = dst.replace(os.sep, '/')

        try:
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
            moved.append(dst)
            logger.debug_func_info(f'File moved: {os.path.basename(src)} → {os.path.basename(dst)}')
        except Exception as e:
            msg = f'Failed to move "{os.path.basename(src)}" → "{os.path.basename(dst)}"'
            logger.error_with_trace(e, f"File move failed: {msg}")
            errors.append(msg)

    return moved, errors

def get_temp_name(comp: str, start: int, end: int) -> str:
    sanitized_name = sanitize_names(comp)
    return f'tmp_{sanitized_name}_{start:04d}_{end:04d}'

def consolidate_outputs(source_dir: str, dest_dir: str, comp: str, start: int, end: int,
                       step: int, ext: str, logger) -> tuple[List[str],
                                                             List[str]]:

    moved, errors = [], []

    if logger:
        logger.debug(f'source_dir={source_dir}, dest_dir={dest_dir}', show_func_info=True)
        logger.debug(f'comp={comp}, start={start}, end={end}, step={step}', show_func_info=True)
        logger.debug('File consolidation: started', show_func_info=True)

    for i in range(start, end + 1, step):
        fs, fe = i, min(i + step - 1, end)
        normalized_source_dir = os.path.abspath(source_dir)
        tmp_dir = os.path.join(normalized_source_dir, get_temp_name(comp, fs, fe))
        tmp_dir = os.path.abspath(tmp_dir).replace(os.sep, '/')
        if logger:
            logger.debug_func_info(f'Looking for tmp_dir={os.path.basename(tmp_dir)}')

        if not os.path.exists(tmp_dir):
            if logger:
                logger.error(f'Missing temp directory: {os.path.basename(tmp_dir)}')
            if os.path.exists(normalized_source_dir):
                contents = os.listdir(normalized_source_dir)
                if logger:
                    logger.debug(f'Source directory contents: {contents}')
            continue

        files = sorted(
            f for f in os.listdir(tmp_dir) if f.lower().endswith(ext)
        )
        if logger:
            logger.debug_func_info(f'Found {len(files)} {ext} files in {os.path.basename(tmp_dir)}')

        if not files:
            logger.warning(f'No {ext.upper()} files found in \"{os.path.basename(tmp_dir)}\"')
            all_files = os.listdir(tmp_dir)
            logger.debug_func_info(f'All files in {tmp_dir}: {all_files}')
            try:
                remove_exist(tmp_dir, logger)
                if logger:
                    logger.info(f'Removed empty temporary directory: {tmp_dir}')
            except Exception as e:
                if logger:
                    logger.warning(f'Failed to remove empty temp directory {tmp_dir}: {e}')
            continue

        m, e = rename_files(tmp_dir, dest_dir, files, comp, fs, logger)
        logger.debug_func_info(f'Moved {len(m)} files, {len(e)} errors')
        moved.extend(m)
        errors.extend(e)

    if len(errors) > 0:
        logger.error(f'Total moved={len(moved)} files, errors={len(errors)}', show_func_info=True)
    else:
        logger.info(f'Total moved={len(moved)} files, errors={len(errors)}', show_func_info=True)
    moved = [(os.path.abspath(f).replace(os.sep, '/')) for f in moved]

    return moved, errors

def get_frame_range(config_frames: Union[int, List[int]], comp_index: int = 0) -> tuple[int, int]:
    if isinstance(config_frames, list):
        return config_frames[comp_index], config_frames[comp_index]
    else:
        return config_frames, config_frames

def get_composition_frames(config, comp_index: int = 0) -> tuple[int, int]:
    start_frame = config.start[comp_index] if isinstance(config.start, list) else config.start
    end_frame = config.end[comp_index] if isinstance(config.end, list) else config.end
    return start_frame, end_frame

def get_result_files(output_dir: str, ext: str) -> List[str]:
    import glob

    try:
        pattern = os.path.join(output_dir, f'*.{ext}').replace(os.sep, '/')
        result_files = sorted(glob.glob(pattern))
        return result_files
    except Exception:
        return []

def load_json_data(json_path: str, section: str = None, 
                   key: str = None, default_value=None, logger=None):
    if logger and section is None:
        logger.info('Loading and validating JSON recipe')
    
    try:
        if not os.path.exists(json_path):
            if section is None:
                err_msg = f'Recipe file not found: {json_path}'
                if logger:
                    logger.error(err_msg)
                Msg.Error(err_msg)
                raise FileNotFoundError(err_msg)
            return default_value
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if section is None:
            required = ['project_settings', 'result_outputs']
            for req_section in required:
                if req_section not in data:
                    err_msg = f'Required section missing: {req_section}'
                    if logger:
                        logger.error(err_msg)
                    Msg.Error(err_msg)
                    raise ValueError(err_msg)
            
            comp_count = len(data['result_outputs'])
            if logger:
                logger.info(f'Recipe loaded: {comp_count} compositions found')
            
            return data
        
        if section not in data:
            return default_value
        
        section_data = data[section]
        
        if key is None:
            return section_data
        
        return section_data.get(key, default_value)
        
    except json.JSONDecodeError as e:
        if section is None:
            err_msg = f'JSON parsing error: {trace_error(e)}'
            if logger:
                logger.error(err_msg)
            Msg.Error(err_msg)
            raise ValueError(err_msg)
        return default_value
    except Exception:
        return default_value
