import psutil
import time
from argparse import ArgumentParser

from configs import Msg

def process_kill_fast(process_keyword: str, kill_flag: bool=False, quiet: bool=True):
    search_count = 0
    terminated_count = 0
    process_keyword_lower = process_keyword.lower()

    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            p_name = proc.info['name'] if 'name' in proc.info else proc.name()
            p_name_lower = p_name.lower()
            if process_keyword_lower in p_name_lower:
                search_count += 1
                
                if kill_flag:
                    try:
                        proc.kill()
                        terminated_count += 1
                        if not quiet:
                            Msg.Green(f'PID {proc.info["pid"]} Process "{p_name}" Force Killed.')
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception:
                        pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue
            
    if not quiet and terminated_count > 0:
        Msg.Info(f'Force killed {terminated_count} processes matching "{process_keyword}"')
    
    return terminated_count > 0

def process_kill(process_keyword: str, kill_flag: bool=False, quiet: bool=True):
    search_count = 0
    terminated_count = 0
    process_keyword_lower = process_keyword.lower()

    if not quiet:
        print(f'-')
        Msg.Dim(f'Searching For Processes With Keyword: \"{process_keyword}\"⋯')

    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            p_name = proc.info['name'] if 'name' in proc.info else proc.name()
            p_name_lower = p_name.lower()
            if process_keyword_lower in p_name_lower:

                search_count += 1
                res_msg = f'Found Process. # {search_count:04d} → PID={proc.info["pid"]}, NAME="{p_name}"'

                if kill_flag:
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                        res_msg += ' Killed Successfully.'
                        terminated_count += 1
                    except psutil.NoSuchProcess:
                        if quiet:
                            Msg.Yellow(f"PID {proc.info['pid']} Process '{p_name}' Already Terminated.")
                    except psutil.AccessDenied:
                        if quiet:
                            Msg.RedPlain(f"PID {proc.info['pid']} Process '{p_name}' Denied")
                        try:
                            proc.kill()
                            proc.wait(timeout=5)
                            if quiet:
                                Msg.Green(f'PID {proc.info["pid"]} Process "{p_name}" Killed Successfully.')
                            terminated_count += 1
                        except Exception as e:
                            if quiet:
                                Msg.RedPlain(f'PID {proc.info["pid"]} Process "{p_name}" Kill Failed Error: {e}')
                    except Exception as e:
                        if quiet:
                            Msg.RedPlain(f'{proc.info["pid"]} Process "{p_name}" Kill Failed Error: {e}')
                else :
                    pass

                if quiet:
                    Msg.Cyan(res_msg)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if quiet:
        if search_count > 0 and not kill_flag:
            Msg.Result(f'{search_count} Processes Found With Keyword: "{process_keyword}"')
        elif terminated_count > 0:
            Msg.Result(f'{terminated_count} Processes Terminated With Keyword: "{process_keyword}"')
        else:
            pass

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
