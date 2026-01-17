
import os
from os import PathLike
import time
from glob import glob
from threading import Thread, Event
from alive_progress import alive_bar

from configs import SystemMonitor

def activate_system_monitor(bar: alive_bar,
                            stop_event: Event, 
                            completion_flag: Event = None) -> Thread:
    def monitor():
        sysmon = SystemMonitor(interval=1.0)
        for usage in sysmon.monitor():
            if stop_event.is_set():
                break
            if completion_flag is None or not completion_flag.is_set():
                bar.text = usage

    t = Thread(target=monitor, daemon=True)
    t.start()
    return t

def get_files_in_progress(base_dir: str, ext: str, comp_name: str = None) -> list[PathLike]:
    if comp_name:
        from scripts._ae_specifics import sanitize_names
        sanitized_comp = sanitize_names(comp_name)
        pattern = os.path.join(base_dir, f'tmp_{sanitized_comp}*', '**', f'*.{ext}')
    else:
        pattern = os.path.join(base_dir, '*', '**', f'*.{ext}')
    return glob(pattern, recursive=True)

def progress_file_monitor(output_dir: str, ext: str, bar: alive_bar,
                          total_count: int,
                          stop_event: Event, title: str = 'RENDER IN PROGRESS…',
                          comp_name: str = None) -> Thread:
    def watcher():
        last_count = 0
        while not stop_event.is_set():
            current_files = get_files_in_progress(output_dir, ext, comp_name)
            current_count = len(current_files)

            if current_count > last_count:
                bar_delta = current_count - last_count
                bar.title = title
                for _ in range(bar_delta):
                    bar()
                last_count = current_count

            if last_count >= total_count:
                break

            time.sleep(0.1)

    t = Thread(target=watcher, daemon=True)
    t.start()
    return t
