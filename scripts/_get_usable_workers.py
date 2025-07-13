import os
import psutil

def get_usable_mem(mem_per_worker:int=3000,
                   mem_reserved:int=8192) -> int:
    '''
    ◦ Calculates max concurrent aerender processes based on system RAM.

    Args:
        mem_per_worker: Expected memory usage per worker in MB (default: 3000MB).
        mem_reserved (int): Amount of RAM to reserve for system overhead in MB (default: 8GB).

    Returns:
        int: The maximum number of executable workers (at least 1 is guaranteed).

    Raise:
        None

    Examples:
        get_usable_mem(mem_per_worker=3000, mem_reserved=8192)
    '''
    total_mem_mb = psutil.virtual_memory().total // (1024 * 1024)
    usable_mem_mb = max(total_mem_mb - mem_reserved, 0)
    return max(1, usable_mem_mb // mem_per_worker)


def get_usable_cpu(reserved_core:int=1) -> int:
    '''
    ◦ Calculates executable aerender tasks based on system CPU.

    Args:
        reserved_core (int): Number of physical cores to reserve for system overhead (default: 1).

    Returns:
        int: The number of executable workers (at least 1 is guaranteed).

    Raises:
        None

    Examples:
        get_usable_cpu(reserved_core=1)
    '''
    cpu_count = psutil.cpu_count(logical=False) or 1    # ← BASED ON PHYSICAL CORE COUNT
    return max(1, cpu_count - reserved_core)


def get_usable_workers(mem_per_worker:int=3000,
                       reserved_mem:int=8192,
                       reserved_core:int=1) -> int:
    '''
    ◦ Calculates optimal aerender workers based on RAM and CPU.

    Args:
        mem_per_worker (int): Expected memory usage per worker in MB (default: 3000MB).
        reserved_mem (int): Amount of RAM to reserve for system overhead in MB (default: 8GB).
        reserved_core (int): Number of physical cores to reserve for system overhead (default: 1).

    Returns:
        int: The number of executable workers (at least 1 is guaranteed).

    Raises:
        None

    Examples:
        get_usable_workers(mem_per_worker=3000, reserved_mem=8192, reserved_core=1)
    '''

    workers_by_mem = get_usable_mem(mem_per_worker, reserved_mem)
    workers_by_cpu = get_usable_cpu(reserved_core)
    return min(workers_by_mem, workers_by_cpu)

if __name__ == '__main__':
    workers = get_usable_workers()
    print(f'Optimal aerender workers (RAM + CPU): {workers}')