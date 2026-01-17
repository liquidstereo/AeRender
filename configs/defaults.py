import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMP_PROJECT_PREFIX = 'temp'

DEFAULT_TEMP_DIR = os.path.join(PROJECT_ROOT, 'tmps')

DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'results')

DEFAULT_DATA_DIR = os.path.join(PROJECT_ROOT, 'process')

DEFAULT_JSON_DIR = os.path.join(DEFAULT_DATA_DIR, 'json')

DEFAULT_LOG_DIR = os.path.join(DEFAULT_DATA_DIR, 'logs')

DEFAULT_SYSTEM_USAGE = 0.70

DEFAULT_RESERVED_CORES = 1

DEFAULT_RESERVED_MEMORY_MB = 8192

DEFAULT_MEMORY_PER_WORKER_MB = 3000

DEFAULT_RS_TEMPLATE = 'Best Settings'

DEFAULT_OM_TEMPLATE = 'YOUR_TEMPLATE'

DEFAULT_VERBOSE_LEVEL = 'ERRORS_AND_PROGRESS'

DEFAULT_FILE_EXTENSION = 'png'

SUPPORTED_IMAGE_FORMATS = ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff']

SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mov', '.avi']

COMPOSITION_NOT_FOUND_ERROR = (
    'Composition name not found in render results. '
    'Processing composition index: {index}, Available compositions: {total}'
)

DEFAULT_VALIDATION_CHUNK_SIZE = 1024

PROGRESS_UPDATE_INTERVAL = 0.1

PREVIEW_CACHE_SIZE = 50

RESIZE_PREVIEW = 0.5

LOG_FILE_ENCODING = 'utf-8'

DEFAULT_FRAME_PADDING = 4

DEFAULT_FRAMES_PER_TASK = 15

PID_LOG_FILENAME = 'aerender_process_pids.log'
