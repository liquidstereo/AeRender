import os
from tabulate import tabulate
from datetime import datetime

def show_result(filepath: str|os.PathLike,
                comp_name: str,
                output_files: str,
                stime: datetime) -> tuple:

    error_files = [f for f in output_files if not os.path.isfile(f)]
    fn, ext = os.path.splitext(os.path.basename(filepath))
    etime = datetime.now() - stime
    elapsed_time = '{}'.format(etime)[:-3]
    table = [[fn+ext,comp_name,str(len(output_files))+' Files',len(error_files),elapsed_time]]
    print(tabulate(table,
                   headers=['AE.FILE','COMP', 'RESULTS', 'ERROR', 'ELAPSED.TIME'],
                   tablefmt='outline'))
    return elapsed_time, error_files