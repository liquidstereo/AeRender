import os
from os import PathLike
from tabulate import tabulate
from datetime import datetime
import wcwidth
from typing import List

from scripts._common import format_elapsed_time

def pad_string_to_width(s: str, width: int, fillchar: str = ' ') -> str:
    ellipsis = '...'
    ellipsis_width = wcwidth.wcswidth(ellipsis)

    current_width = wcwidth.wcswidth(s)
    if current_width == -1:
        return s.ljust(width, fillchar)

    if current_width > width:
        truncated_s = s
        target_content_width = width - ellipsis_width

        if target_content_width < 0:
            return ellipsis[:width] if width >= ellipsis_width else ellipsis[:width]

        while wcwidth.wcswidth(truncated_s) > target_content_width and len(truncated_s) > 0:
            truncated_s = truncated_s[:-1]
        return truncated_s + ellipsis
    else:
        return s + fillchar * (width - current_width)

def show_result(filepath: PathLike, comp_name: str = None,
                output_files: List[PathLike] = None,
                invalid_images: List[PathLike] | None = None,
                stime: datetime = None,
                all_result_info: List[dict] = None,
                enable_logging: bool = False, is_multi: bool = False,
                logger=None, output_dir: str = None, log_fpath: str = None) -> tuple[str, List[PathLike]] | None:
    MAX_WIDTH = 12
    MIN_WIDTH = 5
    
    fn, ext = os.path.splitext(os.path.basename(filepath))
    header_list = [pad_string_to_width('AE.FILE', MAX_WIDTH),
                   pad_string_to_width('COMP', MAX_WIDTH),
                   pad_string_to_width('RESULTS', MAX_WIDTH),
                   pad_string_to_width('ERROR', MIN_WIDTH),
                   pad_string_to_width('ELAPSED.TIME', MAX_WIDTH)]

    if all_result_info is not None:
        table = []
        for i, info in enumerate(all_result_info):
            ae_file = fn + ext if i == 0 else ''
            result_count = info.get("rendered_file_count", len(info.get("result_images", [])))
            expected_count = len(info.get("expected", []))
            error_count = max(0, expected_count - result_count)
            
            table.append([
                pad_string_to_width(ae_file, MAX_WIDTH),
                pad_string_to_width(info['comp_name'], MAX_WIDTH),
                pad_string_to_width(f'{str(result_count)} Files', MAX_WIDTH),
                pad_string_to_width(f'{str(error_count)}', MIN_WIDTH),
                pad_string_to_width(info['elapsed'], MAX_WIDTH)
            ])
    else:
        if comp_name is None or output_files is None or stime is None:
            raise ValueError("단일 컴포지션 모드에서는 comp_name, output_files, stime이 필요합니다")
        
        error_files = []
        for f in output_files:
            normalized_path = os.path.normpath(f)
            if not os.path.isfile(normalized_path):
                error_files.append(f)

        if invalid_images:
            error_files.extend(invalid_images)
        
        elapsed_seconds = (datetime.now() - stime).total_seconds()
        elapsed = format_elapsed_time(elapsed_seconds)
        
        table = [[pad_string_to_width(fn+ext, MAX_WIDTH),
                 pad_string_to_width(comp_name, MAX_WIDTH),
                 pad_string_to_width(f'{str(len(output_files))} Files', MAX_WIDTH),
                 pad_string_to_width(f'{str(len(error_files))}', MIN_WIDTH),
                 pad_string_to_width(elapsed, MAX_WIDTH)]]

    table_str = tabulate(table, headers=header_list, tablefmt='outline', 
                        stralign='left', numalign='left')
    print(table_str)
    
    if enable_logging and table_str and log_fpath:
        try:
            with open(log_fpath, 'a', encoding='utf-8') as log_file:
                log_file.write('-\n')
                for line in table_str.split('\n'):
                    if line.strip():
                        log_file.write(f'{line}\n')
                log_file.write('-\n')
        except Exception:
            pass

    if all_result_info is not None:
        return None
    else:
        return elapsed, error_files
