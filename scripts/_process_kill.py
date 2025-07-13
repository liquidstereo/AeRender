import psutil
import os
import sys
import time
from argparse import ArgumentParser

from alive_progress import alive_bar
from configs import Msg

def process_kill(process_keyword: str, kill_flag: bool=False, quiet: bool=True):
    '''
    ◦ Finds and terminates processes by keyword, ignoring extension and case.

    Args:
        process_keyword (str): Keyword to match in process names (e.g., "AfterFX", "aerender").
        kill_flag (bool): If True, processes are terminated.
        quiet (bool): If True, prints messages to console.

    Returns:
        bool: True if one or more processes were successfully terminated, False otherwise.

    Raises:
        None

    Examples:
        process_kill("AfterFX", kill_flag=True, quiet=True)
    '''
    search_count = 0
    terminated_count = 0
    process_keyword_lower = process_keyword.lower()

    if quiet:
        print(f'-')
        Msg.Dim(f'SEARCHING FOR PROCESSES WITH KEYWORD: \"{process_keyword}\"⋯')


    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            p_name = proc.info['name'] if 'name' in proc.info else proc.name()
            p_name_lower = p_name.lower()
            if process_keyword_lower in p_name_lower:

                search_count += 1
                res_msg = f'FOUND PROCESS. # {search_count:04d} → PID={proc.info["pid"]}, NAME="{p_name}"'

                if kill_flag:
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                        res_msg += ' KILLED SUCCESSFULLY.'
                        terminated_count += 1
                    except psutil.NoSuchProcess:
                        if quiet:
                            Msg.Yellow(f"PID {proc.info['pid']} PROCESS '{p_name}' ALREADY TERMINATED.")
                    except psutil.AccessDenied:
                        if quiet:
                            Msg.RedPlain(f"PID {proc.info['pid']} PROCESS '{p_name}' DENIED")
                        try:
                            proc.kill()
                            proc.wait(timeout=5)
                            if quiet:
                                Msg.Green(f'PID {proc.info["pid"]} PROCESS "{p_name}" KILLED SUCCESSFULLY.')
                            terminated_count += 1
                        except Exception as e:
                            if quiet:
                                Msg.RedPlain(f'PID {proc.info["pid"]} PROCESS "{p_name}" KILL FAILED ERROR: {e}')
                    except Exception as e:
                        if quiet:
                            Msg.RedPlain(f'{proc.info["pid"]} PROCESS "{p_name}" KILL FAILED ERROR: {e}')
                else :
                    pass

                if quiet:
                    Msg.Cyan(res_msg)


        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if quiet:
        if search_count > 0 and not kill_flag:
            Msg.Result(f'{search_count} PROCESSES FOUND WITH KEYWORD: "{process_keyword}"')
        elif terminated_count > 0:
            Msg.Result(f'{terminated_count} PROCESSES TERMINATED WITH KEYWORD: "{process_keyword}"')
        else:
            Msg.Result(f'NO PROCESSES TERMINATED WITH KEYWORD: "{process_keyword}"')

    return terminated_count > 0




def main(args):
    process_keyword = args.search
    kill = args.kill
    quiet = not args.quiet
    process_kill(process_keyword, kill, quiet)

if __name__ == '__main__':
    parser = ArgumentParser(description='DESCRIPTION')
    parser.add_argument(
        '-s',
        '--search',
        type=str,
        default=None,
        required=True,
        help='SEARCH KEYWORD')

    parser.add_argument(
        '-k',
        '--kill',
        action='store_true',
        default=False,
        help='KILL FLAG')

    parser.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        default=False,
        help='SUPPRESS ALL OUTPUT MESSAGES')

    args = parser.parse_args()
    main(args)