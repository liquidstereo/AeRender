import psutil

from configs import (
    DEFAULT_MEMORY_PER_WORKER_MB, DEFAULT_RESERVED_MEMORY_MB,
    DEFAULT_RESERVED_CORES, DEFAULT_SYSTEM_USAGE
)

def get_usable_mem(mem_per_worker: int = DEFAULT_MEMORY_PER_WORKER_MB,
                   mem_reserved: int = DEFAULT_RESERVED_MEMORY_MB) -> int:
    total_mem_mb = psutil.virtual_memory().total // (1024 * 1024)
    usable_mem_mb = max(total_mem_mb - mem_reserved, 0)
    return max(1, usable_mem_mb // mem_per_worker)

def get_usable_cpu(reserved_core: int = DEFAULT_RESERVED_CORES, 
                   default_usage: float = DEFAULT_SYSTEM_USAGE) -> int:
    cpu_count = psutil.cpu_count(logical=False) or 1
    usable_cores = max(1, cpu_count - reserved_core)
    optimal_workers = max(1, int(usable_cores * default_usage))
    return optimal_workers

def get_usable_workers(mem_per_worker: int = DEFAULT_MEMORY_PER_WORKER_MB,
                       reserved_mem: int = DEFAULT_RESERVED_MEMORY_MB,
                       reserved_core: int = DEFAULT_RESERVED_CORES,
                       default_usage: float = DEFAULT_SYSTEM_USAGE) -> int:

    workers_by_mem = get_usable_mem(mem_per_worker, reserved_mem)
    workers_by_cpu = get_usable_cpu(reserved_core, default_usage)
    return min(workers_by_mem, workers_by_cpu)

def get_system_info() -> dict:
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=False) or 1
        
        system_info = {
            'cpu_percent': cpu_percent,
            'cpu_count': cpu_count,
            'memory_percent': memory.percent,
            'memory_total': memory.total,
            'memory_available': memory.available,
            'memory_gb': memory.total / (1024**3),
            'memory_used_gb': memory.used / (1024**3),
            'memory_available_gb': memory.available / (1024**3)
        }
        
        return system_info
        
    except Exception as e:
        return {
            'cpu_percent': 0,
            'cpu_count': 1,
            'memory_percent': 0,
            'memory_total': 8 * (1024**3),
            'memory_available': 4 * (1024**3),
            'memory_gb': 8.0,
            'memory_used_gb': 4.0,
            'memory_available_gb': 4.0
        }

if __name__ == '__main__':
    workers = get_usable_workers()
    print(f'Default Worker Count: {workers}')
    
    system_info = get_system_info()
    print(f'System Info: CPU {system_info["cpu_percent"]}%, Memory {system_info["memory_percent"]}%')
