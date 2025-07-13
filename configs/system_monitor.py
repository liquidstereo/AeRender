import subprocess, psutil
from colorama import Fore, Style, init
init(autoreset=True)

try:
    import pynvml
    NVIDIA_AVAILABLE = True
    pynvml.nvmlInit()
except (ImportError, pynvml.NVMLError):
    NVIDIA_AVAILABLE = False

class SystemMonitor:
    '''
    ◦ Monitors system resource usage, including CPU, RAM, and NVIDIA GPU (if available).

    Usage:
        monitor = SystemMonitor(interval=0.5)
        print(next(monitor.monitor()))
    '''

    def __init__(self, interval: float = 1.0, ram: bool = True, gpu: bool = True):
        '''
        ◦ Initialize the system monitor.

        Args:
            interval: Sampling interval in seconds (default: 1.0)
            ram: Whether to monitor RAM usage
            gpu: Whether to monitor GPU usage (NVIDIA only)
        '''
        self.interval = interval
        self.ram = ram
        self.gpu = gpu and NVIDIA_AVAILABLE
        psutil.cpu_percent(interval=None)  # Prime CPU stat

    def get_gpu_usage(self):
        '''
        ◦ Get GPU utilization and memory usage.

        Returns:
            Tuple(GPU utilization %, GPU memory usage %) or (None, None) if unavailable.
        '''
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
        '''
        ◦ Check if aerender.exe or AfterFX.com is currently using the GPU.

        Returns:
            True if using the GPU, False otherwise.
        '''
        try:
            out = subprocess.run(['nvidia-smi'], capture_output=True,
                                 text=True).stdout.lower()
            for name in ['aerender.exe', 'afterfx.com']:
                if name in out:
                    return True
            return False
        except Exception:
            return False

    def monitor(self):
        '''
        ◦ Generator that yields system usage strings formatted for display.

        Yields:
            String: Includes CPU, RAM (if enabled), GPU usage and CUDA status (if NVIDIA GPU).
        '''
        while True:
            cpu = round(psutil.cpu_percent(self.interval), 3)
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
            yield ' ⬝ '.join(stat)
