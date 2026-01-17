
import subprocess, psutil, time
from colorama import Fore, Style, init
init(autoreset=True)

try:
    import pynvml
    NVIDIA_AVAILABLE = True
    pynvml.nvmlInit()
except (ImportError, pynvml.NVMLError):
    NVIDIA_AVAILABLE = False

class SystemMonitor:

    def __init__(self, interval: float = 1.0, ram: bool = True, gpu: bool = True):
        self.interval = interval
        self.ram = ram
        self.gpu = gpu and NVIDIA_AVAILABLE
        psutil.cpu_percent(interval=None)

    def get_gpu_usage(self):
        if not NVIDIA_AVAILABLE:
            return None, None
        try:
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            u = pynvml.nvmlDeviceGetUtilizationRates(h)
            gpu = f'{u.gpu / 100.0:03.1%}'
            mem = f'{u.memory / 100.0:03.1%}'
            return gpu, mem
        except pynvml.NVMLError:
            return None, None

    @staticmethod
    def is_using_cuda() -> bool:
        try:
            out = subprocess.run(['nvidia-smi'], capture_output=True,
                                 text=True).stdout.lower()
            if 'aerender.exe' in out:
                return True

            return False

        except FileNotFoundError:
            print("Warning: nvidia-smi not found. Cannot check CUDA usage.")
            return False
        except subprocess.CalledProcessError:
            print("Warning: Error running nvidia-smi.")
            return False
        except Exception:
            return False

    def monitor(self):
        while True:
            cpu = round(psutil.cpu_percent(interval=None), 3)
            ram = round(psutil.virtual_memory().percent, 3) if self.ram else None
            gpu, mem = self.get_gpu_usage() if self.gpu else (None, None)

            stat = [f'{Fore.RED}{Style.BRIGHT}CPU: {cpu}%']
            if ram is not None:
                stat.append(f'{Fore.CYAN}RAM: {ram}%')
            if gpu is not None:
                stat.append(f'{Fore.GREEN}GPU: {gpu}')
                stat.append(f'GPU MEMORY: {mem}')
                if self.is_using_cuda():
                    stat.append(f'{Style.BRIGHT}CUDA ENABLED{Style.RESET_ALL}{Fore.RESET}')
                else:
                    stat.append(f'{Style.DIM}CUDA DISABLED{Style.RESET_ALL}{Fore.RESET}')
            else:
                stat.append(f'{Fore.MAGENTA}NON-CUDA GPU{Style.RESET_ALL}{Fore.RESET}')
            yield ' · '.join(stat)
            time.sleep(self.interval)
