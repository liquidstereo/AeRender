
import sys
from .preview.preview_result import preview_result

def render_preview(preview_data: dict, result_success: bool = True):
    from configs import Msg
    
    if not (preview_data and result_success):
        return
        
    try:
        mode = preview_data.get('mode')
        
        if mode == 'single':
            img_paths = preview_data.get('img_paths', [])
            if img_paths:
                preview_result(img_list=img_paths)
            
        elif mode == 'multi':
            comp_names = preview_data.get('comp_names', [])
            comp_data = preview_data.get('comp_data', [])
            if comp_names and comp_data:
                multi_comp_data = {
                    'comp_names': comp_names,
                    'comp_data': comp_data
                }
                preview_result(multi_comp_data=multi_comp_data)
            
    except Exception as e:
        Msg.Warning(f'Preview failed but rendering completed: {e}')

def preview_standalone(json_paths_override: list = None) -> int:
    return 0

if __name__ == '__main__':
    sys.exit(preview_standalone())
