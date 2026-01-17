from dataclasses import dataclass, field
import time
from typing import Optional, List, Dict, Any

@dataclass
class PreviewState:
    current_index: int = 0
    paused: bool = False
    zoom_level: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    zoom_info_text: Optional[str] = None
    zoom_info_timer: float = 0.0
    pan_step: float = 0.1
    
    is_multi_comp: bool = False
    current_comp_index: int = 0
    comp_names: List[str] = field(default_factory=list)
    comp_data_list: List[Dict[str, Any]] = field(default_factory=list)

    _default_zoom_level: float = field(init=False)
    _default_pan_x: float = field(init=False)
    _default_pan_y: float = field(init=False)
    _default_current_index: int = field(init=False)
    _default_paused: bool = field(init=False)

    def __post_init__(self):
        self._default_zoom_level = self.zoom_level
        self._default_pan_x = self.pan_x
        self._default_pan_y = self.pan_y
        self._default_current_index = self.current_index
        self._default_paused = self.paused

    def reset_to_defaults(self):
        self.zoom_level = self._default_zoom_level
        self.pan_x = self._default_pan_x
        self.pan_y = self._default_pan_y
        self.current_index = self._default_current_index
        self.paused = self._default_paused
        self.zoom_info_text = None
        self.zoom_info_timer = 0.0

    def update_zoom(self, direction: str):
        if direction == 'in':
            self.zoom_level = min(5.0, self.zoom_level + 0.1)
        elif direction == 'out':
            self.zoom_level = max(0.1, self.zoom_level - 0.1)
        self.zoom_info_text = f"ZOOM: {self.zoom_level:.1f}x"
        self.zoom_info_timer = time.time()

    def clear_zoom_info(self):
        if time.time() - self.zoom_info_timer >= 2.0:
            self.zoom_info_text = None
            self.zoom_info_timer = 0.0

    def update_pan(self, action: str):
        if action == 'pan_up':
            self.pan_y = max(-1.0, self.pan_y - self.pan_step)
        elif action == 'pan_down':
            self.pan_y = min(1.0, self.pan_y + self.pan_step)
        elif action == 'pan_left':
            self.pan_x = max(-1.0, self.pan_x - self.pan_step)
        elif action == 'pan_right':
            self.pan_x = min(1.0, self.pan_x + self.pan_step)
        elif action == 'pan_reset':
            self.pan_x = self._default_pan_x
            self.pan_y = self._default_pan_y

    def setup_multi_comp(self, comp_names: List[str], comp_data_list: List[Dict[str, Any]]):
        self.is_multi_comp = True
        self.comp_names = comp_names
        self.comp_data_list = comp_data_list
        self.current_comp_index = 0

    def next_comp(self) -> bool:
        if not self.is_multi_comp or not self.comp_names:
            return False
        
        self.current_comp_index = (self.current_comp_index + 1) % len(self.comp_names)
        self.current_index = 0
        return True

    def prev_comp(self) -> bool:
        if not self.is_multi_comp or not self.comp_names:
            return False
        
        self.current_comp_index = (self.current_comp_index - 1) % len(self.comp_names)
        self.current_index = 0
        return True

    def get_current_comp_name(self) -> str:
        if not self.is_multi_comp or not self.comp_names:
            return ""
        return self.comp_names[self.current_comp_index]

    def get_current_comp_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_multi_comp or not self.comp_data_list:
            return None
        if self.current_comp_index >= len(self.comp_data_list):
            return None
        return self.comp_data_list[self.current_comp_index]

    def get_comp_info_text(self) -> str:
        if not self.is_multi_comp or not self.comp_names:
            return ""
        
        current_name = self.get_current_comp_name()
        comp_number = self.current_comp_index + 1
        total_comps = len(self.comp_names)
        
        return f"{current_name} ({comp_number}/{total_comps})"
