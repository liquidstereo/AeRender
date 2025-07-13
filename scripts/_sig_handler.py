import os, sys, time
import re
import psutil
import signal
import platform
import subprocess

from scripts._process_kill import process_kill
from configs import Msg

'''
_sig_handler.py

Signal and process cleanup utility for After Effects rendering processes.
Tracks aerender/AfterFX processes and handles termination gracefully.
'''

TARGET_PROCS = ['aerender.exe', 'aerender', 'afterfx.com']
MAX_KILL_CYCLES = 10
PID_LOG_PATH = './process_pids.log'

_tracked_pids, _main_pid = [], os.getpid()
_interrupt_msg_shown = False


def save_pids_to_log(pid: int, path: str=PID_LOG_PATH) -> str:
    '''
    ◦ Saves a process PID to the log file.

    Args:
        pid (int): Process ID to save.
        path (str): Path to the log file. Defaults to PID_LOG_PATH.

    Returns:
        str: Path to the log file.

    Examples:
        save_pids_to_log(12345)
    '''
    try:
        with open(path, 'a') as f:
            f.write(f'PID: {pid}\n')
    except IOError:
        pass
    return path


def get_pids_from_log(path: str=PID_LOG_PATH) -> list[int]:
    '''
    ◦ Retrieves PIDs from the log file.

    Args:
        path (str): Path to the log file. Defaults to PID_LOG_PATH.

    Returns:
        list[int]: List of PIDs found in the log.

    Examples:
        pids = get_pids_from_log()
    '''
    pids = []
    try:
        with open(path, 'r') as f:
            for line in f:
                m = re.search(r'PID: (\d+)', line)
                if m:
                    pids.append(int(m.group(1)))
    except FileNotFoundError:
        pass
    except Exception as e:
        Msg.Error(f'Error reading file: {e}')
    return pids


def remove_pids_from_log(pids: list[int], path: str=PID_LOG_PATH):
    '''
    ◦ Removes specific PIDs from the log file.

    Args:
        pids (list[int]): List of PIDs to remove.
        path (str): Path to the log file. Defaults to PID_LOG_PATH.

    Examples:
        remove_pids_from_log([12345])
    '''
    if not os.path.exists(path):
        return
    tmp = path + '.tmp'
    try:
        with open(path, 'r') as inp, open(tmp, 'w') as out:
            for line in inp:
                m = re.search(r'PID: (\d+)', line)
                if m and int(m.group(1)) in pids:
                    continue
                out.write(line)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)


def clear_log_file(path: str=PID_LOG_PATH):
    '''
    ◦ Deletes the PID log file.

    Args:
        path (str): Path to the log file.

    Examples:
        clear_log_file()
    '''
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            Msg.Error(f'ERROR CLEARING FILE: {e}')


def add_tracked_pid(pid: int):
    '''
    ◦ Tracks a new PID and saves it to the log.

    Args:
        pid (int): PID to track.

    Examples:
        add_tracked_pid(12345)
    '''
    _tracked_pids.append(pid)
    save_pids_to_log(pid)


def _kill_tracked():
    '''
    ◦ Kills all tracked PIDs in _tracked_pids list.

    Examples:
        _kill_tracked()
    '''
    for pid in _tracked_pids:
        try:
            psutil.Process(pid).kill()
        except psutil.NoSuchProcess:
            pass
    _tracked_pids.clear()


def _kill_by_name():
    '''
    ◦ Terminates known target processes by name.

    Examples:
        _kill_by_name()
    '''
    for _ in range(MAX_KILL_CYCLES):
        found = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() in TARGET_PROCS:
                    psutil.Process(proc.info['pid']).terminate()
                    found = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if not found:
            return
        time.sleep(0.25)
    _force_kill_windows()


def _force_kill_windows():
    '''
    ◦ Force kill processes by name using taskkill on Windows.

    Examples:
        _force_kill_windows()
    '''
    if platform.system() != 'Windows':
        return
    for name in TARGET_PROCS:
        try:
            subprocess.run(
                ['taskkill', '/F', '/IM', name],
                check=False, capture_output=True
            )
        except FileNotFoundError:
            pass


def kill_process_tree(pid: int):
    '''
    ◦ Kills the given process and all of its children.

    Args:
        pid (int): Parent process ID.

    Examples:
        kill_process_tree(45678)
    '''
    try:
        proc = psutil.Process(pid)
        for child in proc.children(recursive=True):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        proc.kill()
    except psutil.NoSuchProcess:
        pass


def _cleanup_processes():
    '''
    ◦ Cleans up all tracked and named aerender-related processes.

    Examples:
        _cleanup_processes()
    '''
    _kill_by_name()
    for name in TARGET_PROCS:
        process_kill(name, True, quiet=False)
    for pid in get_pids_from_log():
        kill_process_tree(pid)
    remove_pids_from_log(pids=get_pids_from_log())
    _kill_tracked()


def worker_handler():
    '''
    ◦ Signal handler setup for worker processes.

    Examples:
        worker_handler()
    '''
    def handler(sig, frame):
        _cleanup_processes()
        sys.exit(0)
    signal.signal(signal.SIGINT, handler)


def setup_handler(logger):
    '''
    ◦ Main SIGINT handler setup for graceful Ctrl+C interrupt.

    Examples:
        setup_handler()
    '''
    def handler(sig, frame):
        global _interrupt_msg_shown
        if os.getpid() != _main_pid or _interrupt_msg_shown:
            return
        _interrupt_msg_shown = True
        # m = (
        #     f'{"-"*50}\n'
        #     f'PROCESS INTERRUPTED BY USER. CLEANING UP...\n'
        #     f'PLEASE WAIT WHILE FINISHING UP THE PROCESSES.\n'
        #     f'{"-"*50}\n'
        # )
        # Msg.Red(m)

        logger.error(f'\nPROCESS INTERRUPTED BY USER.')
        _cleanup_processes()
        clear_log_file(path=PID_LOG_PATH)
        sys.exit(1)
    signal.signal(signal.SIGINT, handler)
