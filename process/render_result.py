
import os
import json
import shutil
from typing import Dict, Any, List

from configs import Msg
from scripts._show_result import show_result
from scripts._ae_specifics import load_json_data
from .render_preflight import verify_processes

def cleanup_log_file(logger, keep_log: bool = True) -> bool:
    if keep_log:
        return True

    try:
        if logger and hasattr(logger, 'filepath'):
            log_path = logger.filepath
            if log_path and os.path.exists(log_path):
                os.remove(log_path)

                log_dir = os.path.dirname(log_path)
                if log_dir and os.path.exists(log_dir):
                    if not os.listdir(log_dir):
                        shutil.rmtree(log_dir)

                return True
    except Exception:
        pass

    return False

def get_comp_names(recipe: dict) -> List[str]:
    settings = recipe.get('project_settings', {})
    comps = settings.get('compositions', '')

    if isinstance(comps, str):
        if ',' not in comps:
            return [comps]
        return [c.strip() for c in comps.split(',')]
    elif isinstance(comps, list):
        return comps
    return []

def get_verified_imgs(outputs: dict, name: str) -> List[str]:
    paths = []

    if name in outputs:
        frames = outputs[name].get('frames', {})
        for num, info in frames.items():
            if info.get('verified', False):
                path = info.get('result')
                if path and os.path.exists(path):
                    paths.append(path)

    return paths

def calc_stats(outputs: dict, name: str) -> dict:
    data = outputs.get(name, {})

    frames = data.get('frames', {})
    verified = sum(1 for frame in frames.values()
                  if frame.get('verified', False))

    total = data.get('total', 0)
    errors = max(0, total - verified)
    elapsed = data.get('elapsed_time', '00:00:00')

    return {
        'verified': verified,
        'total': total,
        'errors': errors,
        'elapsed': elapsed
    }

def get_render_data(names: List[str], imgs: List[List[str]]) -> dict:
    all_paths = []
    comp_data = []

    for i in range(len(names)):
        files = imgs[i] if i < len(imgs) else []
        all_paths.extend(files)

        fnames = [os.path.basename(p) for p in files] if files else []
        comp_data.append({
            'fnames': files,
            'images': fnames
        })

    multi = len(names) > 1

    if multi and comp_data:
        return {
            'mode': 'multi',
            'comp_names': names,
            'comp_data': comp_data
        }
    elif all_paths:
        return {
            'mode': 'single',
            'img_paths': all_paths
        }
    else:
        return {}

def update_json(outputs: dict, stats: List[dict], names: List[str]) -> None:
    for i, name in enumerate(names):
        if name in outputs and i < len(stats):
            outputs[name]['completed'] = stats[i]['verified']

def save_json(path: str, recipe: dict) -> None:
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(recipe, f, indent=2, ensure_ascii=False)
    except Exception as e:
        Msg.Warning(f'Failed to update JSON file: {e}')

def render_result(json_path: str, results: Dict[str, Any],
                  logs: bool = False, logger=None) -> tuple[bool, dict]:
    try:
        recipe = load_json_data(json_path)
        if not recipe:
            Msg.Error(f'Failed to load JSON recipe: {json_path}')
            return False, {}

        settings = recipe.get('project_settings', {})
        ae_file = settings.get('project_file', '')
        names = get_comp_names(recipe)

        if not names:
            Msg.Error('No compositions found in recipe')
            return False, {}

        outputs = recipe.get('result_outputs', {})
        comp_results = results.get('composition_results', {})

        info_list = []
        stats_list = []
        all_imgs = []

        for name in names:
            imgs = get_verified_imgs(outputs, name)
            all_imgs.append(imgs)

            stats = calc_stats(outputs, name)
            stats_list.append(stats)

            info = {
                'comp_name': name,
                'rendered_file_count': stats['verified'],
                'expected': comp_results.get(name, {}).get('expected_files', []),
                'result_images': imgs,
                'elapsed': stats['elapsed']
            }
            info_list.append(info)

        update_json(outputs, stats_list, names)
        save_json(json_path, recipe)

        multi = len(names) > 1
        show_result(
            filepath=ae_file,
            all_result_info=info_list,
            enable_logging=logs,
            is_multi=multi,
            logger=logger,
            log_fpath=recipe.get('log_file')
        )

        render_data = get_render_data(names, all_imgs)

        try:
            aerender_cleanup = verify_processes(logger)
            if aerender_cleanup.get('terminated', False):
                if logger:
                    logger.info('Cleanup: terminated remaining aerender.exe')
        except Exception as e:
            if logger:
                logger.warning(f'Failed to cleanup aerender processes: {e}')

        cleanup_log_file(logger, keep_log=logs)

        return True, render_data

    except Exception as e:
        Msg.Error(f'Failed to display render results: {e}')
        if logger:
            logger.error(f'Render result display error: {e}')

        try:
            aerender_cleanup = verify_processes(logger)
            if aerender_cleanup.get('terminated', False):
                if logger:
                    logger.info('Cleanup: terminated remaining aerender.exe')
        except Exception:
            pass

        cleanup_log_file(logger, keep_log=logs)

        return False, {}

def main():
    import sys
    if len(sys.argv) < 2:
        print('Usage: python render_result.py <json_path>')
        sys.exit(1)

    json_path = sys.argv[1]
    test_results = {
        'overall_success': True,
        'composition_results': {
            'Comp 1': {
                'valid_count': 100,
                'expected_files': [f'frame_{i:04d}.png'
                                   for i in range(100)],
                'valid_files': [f'frame_{i:04d}.png'
                                for i in range(100)],
                'invalid_files': [],
                'elapsed_time': '00:05:30'
            }
        }
    }

    success, preview_data = render_result(json_path, test_results)
    print(f'Result display success: {success}')
    print(f'Preview data: {preview_data}')

if __name__ == '__main__':
    main()
