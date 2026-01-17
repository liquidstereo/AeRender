import os
import sys
import time
import re
import psutil
import signal
import platform
import subprocess
import atexit
import threading

from configs import Msg, DEFAULT_TEMP_DIR, PID_LOG_FILENAME

from scripts._process_kill import process_kill
from scripts._common import abs_path, remove_exist

TARGET_PROCS = ['aerender.exe', 'aerender', 'afterfx.com']
MAX_KILL_CYCLES = 10
PID_LOG_PATH = abs_path(os.path.join(DEFAULT_TEMP_DIR, PID_LOG_FILENAME))

_tracked_pids, _main_pid = [], os.getpid()
_interrupt_msg_shown = False
_shutdown_event = threading.Event()
_cleanup_registered = False

def save_pids_to_log(pid: int, path: str=PID_LOG_PATH) -> str:
    try:
        log_dir = os.path.dirname(path)
        os.makedirs(log_dir, exist_ok=True)

        with open(path, 'a') as f:
            f.write(f'PID: {pid}\n')
    except (IOError, PermissionError, OSError):
        pass
    return path

def get_pids_from_log(path: str=PID_LOG_PATH) -> list[int]:
    pids = []
    try:
        with open(path, 'r') as f:
            for line in f:
                m = re.search(r'PID: (\d+)', line)
                if m:
                    pids.append(int(m.group(1)))
    except FileNotFoundError:
        pass
    except PermissionError:
        pass
    except Exception as e:
        Msg.Error(f'Error reading file: {e}')
    return pids

def remove_pids_from_log(pids: list[int], path: str=PID_LOG_PATH):
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
    except:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except:
            pass

def clear_log_file(path: str=PID_LOG_PATH):
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            Msg.Error(f'ERROR CLEARING FILE: {e}')

def add_tracked_pid(pid: int):
    _tracked_pids.append(pid)
    save_pids_to_log(pid)

def _kill_tracked():
    for pid in _tracked_pids:
        try:
            psutil.Process(pid).kill()
        except psutil.NoSuchProcess:
            pass
    _tracked_pids.clear()

def _kill_by_name():
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
    _kill_by_name()
    for name in TARGET_PROCS:
        process_kill(name, True, quiet=True)
    for pid in get_pids_from_log():
        kill_process_tree(pid)
    remove_pids_from_log(pids=get_pids_from_log())
    _kill_tracked()

def worker_handler():
    def handler(sig, frame):
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'aerender.exe'],
                          capture_output=True, check=False, timeout=1)
        except:
            pass
        sys.exit(0)
    signal.signal(signal.SIGINT, handler)

def _emergency_cleanup(temp_dir=None):
    global _shutdown_event
    if _shutdown_event.is_set():
        return
    _shutdown_event.set()

    try:
        from process.render_cleanup import force_clean_temps
        if temp_dir:
            force_clean_temps(temp_dir)
        else:
            force_clean_temps()

        subprocess.run(['taskkill', '/F', '/IM', 'aerender.exe'],
                      capture_output=True, check=False, timeout=1)
    except:
        pass

def _stanby_process_termination(timeout=3.0):
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            found_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() in TARGET_PROCS:
                        found_processes.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not found_processes:
                return True

            if platform.system() == 'Windows':
                for proc_name in TARGET_PROCS:
                    subprocess.run(['taskkill', '/F', '/IM', proc_name],
                                  capture_output=True, check=False, timeout=1)

            time.sleep(0.1)

        except:
            break

    return False

def _stanby_cleaned_up(temp_dir=DEFAULT_TEMP_DIR, timeout=5.0):
    from process.render_cleanup import clean_temps
    return clean_temps(temp_dir, timeout)

def setup_handler(logger, temp_dir=DEFAULT_TEMP_DIR):
    global _cleanup_registered, _shutdown_event

    if not _cleanup_registered:
        atexit.register(_emergency_cleanup, temp_dir)
        _cleanup_registered = True

    def handler(sig, frame):
        global _interrupt_msg_shown, _shutdown_event
        if os.getpid() != _main_pid or _interrupt_msg_shown or _shutdown_event.is_set():
            return

        _interrupt_msg_shown = True
        _shutdown_event.set()

        _cleanup_processes()
        process_terminated = _stanby_process_termination()

        tmps_removed = _stanby_cleaned_up(temp_dir)

        err_msg = 'Process Interrupted By User. '
        if process_terminated and tmps_removed:
            err_msg += 'Temp Files Have Been Removed.'
        elif not process_terminated:
            err_msg += 'Some processes may still be running.'
        elif not tmps_removed:
            err_msg += 'Temporary files cleanup incomplete.'

        Msg.Error(err_msg)

        os._exit(1)

    signal.signal(signal.SIGINT, handler)

def is_shutdown_requested():
    return _shutdown_event.is_set()

def reset_shutdown_event():
    global _shutdown_event
    _shutdown_event.clear()
