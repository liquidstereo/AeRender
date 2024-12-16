import os, sys, time
import psutil
from alive_progress import alive_bar
from colorama import Fore, Style, init
init(autoreset=True)

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from configs import Logger


def sys_info(arg: str=None) -> str :
    ram_usage = psutil.virtual_memory()[2]
    cpu_usage = psutil.cpu_percent(1)
    cpu_ram_usage = f'CPU: {cpu_usage}%, RAM: {ram_usage}%'
    if arg == 'ram' :
        return f'{ram_usage}%'
    elif arg == 'cpu' :
        return f'{cpu_usage}%'
    else :
        return cpu_ram_usage


def progress_bar(files: list[str|os.PathLike], logger: Logger) -> None :
    results = []
    progress_value = 0
    with alive_bar(len(files),
                # spinner=None,
                title='PLEASE WAIT...',
                title_length=18,
                length=20,
                dual_line=True,
                stats=True, elapsed=True,
                manual=True,
                enrich_print=True) as bar:

        while True:
            sys_usage = sys_info()
            bar_text = (
                f'{Style.DIM}{sys_usage}'
                f' (WAITING FOR PROCESSES...)'
                f'{Style.RESET_ALL}')
            bar.text = bar_text
            for i in range(0, len(files), 1):
                if os.path.isfile(files[i]) and files[i] not in results :
                    results.append(files[i])
                    logger.debug(f'Process: \"{files[i]}\"')
                    fn, ext = os.path.splitext(os.path.basename(files[i]))
                    result_file = f'\"{fn}{ext}\"'
                    bar.title = 'PROCESSING...'
                    bar.text = (f'{Fore.RED}{sys_usage}'
                                f' (PROCESS: {result_file})'
                                f'{Fore.RESET}')
                progress_value = len(results) / len(files)
                bar(progress_value)
            if progress_value >= 1 :
                bar.title = 'PROCESS COMPLETED.'
                bar.text = None
                break
            time.sleep(0.1)