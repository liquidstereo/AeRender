
import os
from argparse import ArgumentParser
from configs.render_config import RenderConfig
from configs.defaults import (
    DEFAULT_OUTPUT_DIR, DEFAULT_RS_TEMPLATE, DEFAULT_OM_TEMPLATE, 
    DEFAULT_VERBOSE_LEVEL, DEFAULT_FILE_EXTENSION
)
from scripts._ae_specifics import parse_multi_values, has_multiple_values

def parse_arguments() -> RenderConfig:
    parser = ArgumentParser(
        description='Python script for multicore After Effects rendering.'
    )
    parser.add_argument(
        '-f', '--fpath', required=True, help='PROJECT FILE PATH'
    )
    parser.add_argument(
        '-c', '--comp_name', required=True, help='COMPOSITION NAME (single name, comma-separated or space-separated list)'
    )
    parser.add_argument(
        '-o', '--output_dir', default=None, help=f'OUTPUT DIRECTORY (default: {DEFAULT_OUTPUT_DIR}/COMP_NAME)'
    )
    parser.add_argument(
        '-s', '--start', required=True, nargs='+', help='START FRAME (single number or space-separated list, e.g., -s 0 or -s 0 1 2)'
    )
    parser.add_argument(
        '-e', '--end', required=True, nargs='+', help='END FRAME (single number or space-separated list, e.g., -e 10 or -e 10 11 12)'
    )
    parser.add_argument(
        '-w', '--workers', type=int, default=0,
        help='Number of worker processes (0 for auto-detect)'
    )
    parser.add_argument(
        '-t', '--per_task', type=int, default=0,
        help='Number of frames per task (0 for auto-detect)'
    )
    parser.add_argument(
        '-rst', '--rs_template', default=DEFAULT_RS_TEMPLATE,
        help='Render Setting preset'
    )
    parser.add_argument(
        '-omt', '--om_template', default=DEFAULT_OM_TEMPLATE,
        help='Output Module preset'
    )
    parser.add_argument(
        '-x', '--ext', default=DEFAULT_FILE_EXTENSION,
        help='File extension for output'
    )
    parser.add_argument(
        '-v', '--verbose', default=DEFAULT_VERBOSE_LEVEL,
        help='After Effects verbose flag'
    )
    parser.add_argument(
        '-p', '--preview', action='store_true',
        help='Preview result after rendering'
    )
    parser.add_argument(
        '-l', '--logs', action='store_true', default=False,
        help='Generate log files (default: False)'
    )
    parser.add_argument(
        '-json', '--save_json', action='store_true', default=False,
        help='Save render configuration as JSON file (default: False)'
    )

    args = parser.parse_args()

    if args.output_dir is None:
        base_dir = os.path.abspath(DEFAULT_OUTPUT_DIR)
    else:
        base_dir = os.path.abspath(args.output_dir)

    if has_multiple_values(args.comp_name):
        comp_names = parse_multi_values(args.comp_name)
        args.output_dir = ','.join([os.path.join(base_dir, comp.strip()) for comp in comp_names])
        args.comp_name = ','.join(comp_names)
    else:
        args.output_dir = os.path.join(base_dir, args.comp_name.strip())

    if isinstance(args.start, list):
        args.start = ' '.join(args.start)
    if isinstance(args.end, list):
        args.end = ' '.join(args.end)

    return RenderConfig(**vars(args))
