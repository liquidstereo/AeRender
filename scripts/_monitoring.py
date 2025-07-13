import os
from os import PathLike
import time
from glob import glob
from threading import Thread, Event
from alive_progress import alive_bar

from configs import SystemMonitor

def activate_system_monitor(bar: alive_bar,
                            stop_event: Event) -> Thread:
    '''
    ◦ Activate system monitor.

    Args:
        bar: Alive Progress Bar
        stop_event: Event to stop monitoring

    Returns:
        threading.Thread: Thread object for system monitor

    Raise:
        None

    Examples:
        activate_system_monitor(bar, stop_event)

    '''
    def monitor():
        sysmon = SystemMonitor(interval=1.0)
        for usage in sysmon.monitor():
            if stop_event.is_set():
                break
            bar.text = usage

    t = Thread(target=monitor, daemon=True)
    t.start()
    return t


def get_files_in_progress(base_dir: str, ext: str) -> list[PathLike]:
    '''
    ◦ Get files in progress.

    Args:
        base_dir: Base directory path
        ext: File extension

    Returns:
        list[PathLike]: List of files in progress

    Raise:
        None

    Examples:
        get_files_in_progress('C:/tmp', 'png')
    '''
    pattern = os.path.join(base_dir, '*', '**', f'*.{ext}')
    return glob(pattern, recursive=True)


def progress_file_monitor(output_dir: str, ext: str, bar: alive_bar,
                          total_count: int,
                          stop_event: Event) -> Thread:
    '''
    ◦ Progress file monitor.

    Args:
        output_dir: Output directory path
        ext: File extension
        bar: Alive Progress Bar
        total_count: Total count
        stop_event: Event to stop monitoring

    Returns:
        threading.Thread: Thread object for file monitor

    Raise:
        None

    Examples:
        progress_file_monitor('C:/tmp', 'png', bar, 100, stop_event)
    '''
    def watcher():
        last_count = 0
        while not stop_event.is_set():
            current_files = get_files_in_progress(output_dir, ext)
            current_count = len(current_files)

            if current_count > last_count:
                bar_delta = current_count - last_count
                bar.title = 'RENDER IN PROGRESS...'
                for _ in range(bar_delta):
                    bar()
                last_count = current_count

            if last_count >= total_count:
                break

            time.sleep(0.1)    # ← INTERVAL

    t = Thread(target=watcher, daemon=True)
    t.start()
    return t