import os, sys
import cv2
import numpy as np
import time
from typing import List, Union, Optional

from ._preview_state import PreviewState
from ._preview_utils import get_output_format, calculate_pan_offset

class PreviewRenderer:
    def __init__(self, resize: bool, resize_value: float,
                 text_padding: int, text_line_spacing: int, font_size: float,
                 custom_window_title: Optional[str], set_text: Optional[tuple],
                 fixed_title: Optional[str] = None):
        self.resize = resize
        self.resize_value = resize_value
        self.text_padding = text_padding
        self.text_line_spacing = text_line_spacing
        self.font_size = font_size
        self.custom_window_title = custom_window_title
        self.set_text = set_text
        self._fixed_title = fixed_title

    def render_frame(self, img: np.ndarray, filename: str,
                     total_count: int, state: PreviewState,
                     current_fps: float) -> tuple[np.ndarray, str]:
        h, w = img.shape[:2]

        if self.resize:
            final_w, final_h = int(w * self.resize_value), int(h * self.resize_value)
        else:
            final_w, final_h = w, h

        if state.zoom_level != 1.0:
            zoom_w, zoom_h = int(final_w * state.zoom_level), int(final_h * state.zoom_level)
            img_resized = cv2.resize(img, (final_w, final_h), interpolation=cv2.INTER_AREA)
            img_zoomed = cv2.resize(img_resized, (zoom_w, zoom_h), interpolation=cv2.INTER_LINEAR)
        else:
            img_zoomed = cv2.resize(img, (final_w, final_h), interpolation=cv2.INTER_AREA)
            zoom_w, zoom_h = final_w, final_h

        if state.zoom_level > 1.0:
            start_x, start_y = calculate_pan_offset(
                state.pan_x, state.pan_y, zoom_w, zoom_h, final_w, final_h
            )
            end_x = start_x + final_w
            end_y = start_y + final_h
            img_display = img_zoomed[start_y:end_y, start_x:end_x]
        elif state.zoom_level < 1.0:
            img_display = np.zeros((final_h, final_w, 3), dtype=np.uint8)

            start_x = max(0, (final_w - zoom_w) // 2)
            start_y = max(0, (final_h - zoom_h) // 2)
            end_x = min(final_w, start_x + zoom_w)
            end_y = min(final_h, start_y + zoom_h)

            actual_w = end_x - start_x
            actual_h = end_y - start_y

            if actual_w > 0 and actual_h > 0 and actual_w <= zoom_w and actual_h <= zoom_h:
                img_display[start_y:end_y, start_x:end_x] = img_zoomed[:actual_h, :actual_w]
        else:
            img_display = img_zoomed

        if self.set_text and isinstance(self.set_text, list) and len(self.set_text) > 0:
            self._insert_multiple_texts(
                img_display, self.set_text,
                filename=filename, current_fps=current_fps,
                current_index=state.current_index, total_count=total_count,
                paused=state.paused, state=state
            )
        elif self.set_text and isinstance(self.set_text, (tuple, list)) and len(self.set_text) >= 2:
            custom_text, position = self.set_text[0], self.set_text[1]
            self._insert_text_at_position(img_display, custom_text, position, state=state)

        if self._fixed_title:
            encoded_title = self._fixed_title
        else:
            if self.custom_window_title:
                format_pattern = get_output_format(filename) or f"preview_result_{filename}"
                
                results_dir = os.path.basename(os.path.dirname(filename)) if filename else "Unknown"
                
                try:
                    title = self.custom_window_title.format(
                        filename=os.path.basename(filename) if filename else "Unknown",
                        results_dir=results_dir,
                        format=format_pattern,
                        width=w,
                        height=h,
                        resize_value=self.resize_value,
                        status="PAUSED" if state.paused else "PLAYING",
                        fps=f"{current_fps:05.2f}" if current_fps > 0 and not state.paused else "PAUSED",
                        frame_index=f"{state.current_index + 1:04d}/{total_count:04d}" if total_count > 0 else "N/A"
                    )
                except (KeyError, ValueError):
                    title = self.custom_window_title
            else:
                format_pattern = get_output_format(filename) or f"preview_result_{filename}"
                title = f'Preview: {format_pattern} ({w} X {h})'

            try:
                encoded_title = title.encode('utf-8').decode(sys.getfilesystemencoding())
            except (UnicodeEncodeError, UnicodeDecodeError):
                encoded_title = title
            self._fixed_title = encoded_title

        return img_display, encoded_title

    def _insert_multiple_texts(self, img_display: np.ndarray, text_list: list,
                             filename: str = "", current_fps: float = 0.0,
                             current_index: int = 0, total_count: int = 0,
                             paused: bool = False, state: PreviewState = None) -> None:
        h, w = img_display.shape[:2]

        position_offsets = {
            'bottom-left': 0,
            'bottom-right': 0,
            'top-left': 0,
            'top-right': 0
        }

        line_spacing = self.text_line_spacing

        status_text = "PAUSED" if paused else "PLAYING"
        frame_index = f"{current_index + 1:04d}/{total_count:04d}" if total_count > 0 else "N/A"
        fps_text = f"{current_fps:05.2f}" if current_fps > 0 and not paused else "PAUSED"
        
        comp_info = ""
        if state and state.is_multi_comp:
            comp_info = state.get_comp_info_text()

        for text_item in text_list:
            if isinstance(text_item, (tuple, list)) and len(text_item) >= 2:
                template_text, position = text_item[0], text_item[1]

                try:
                    actual_text = template_text.format(
                        filename=filename,
                        status=status_text,
                        fps=fps_text,
                        frame_index=frame_index,
                        comp_info=comp_info
                    )
                except (KeyError, ValueError):
                    actual_text = template_text

                current_offset = position_offsets.get(position, 0)
                self._insert_text_at_position_with_offset(
                    img_display, actual_text, position, current_offset, state=state
                )
                position_offsets[position] = current_offset + line_spacing

        if state and state.zoom_info_text:
            if time.time() - state.zoom_info_timer < 2.0:
                current_offset = position_offsets.get('top-left', 0)
                self._insert_text_at_position_with_offset(
                    img_display, state.zoom_info_text, 'top-left', current_offset, state=state
                )
            else:
                state.zoom_info_text = None
        

    def _insert_text_at_position_with_offset(self, img_display: np.ndarray, text: str,
                                           position: str, y_offset: int = 0, state: PreviewState = None) -> None:
        h, w = img_display.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = self.font_size
        font_thickness = 1
        text_color = (255, 255, 255)
        text_color_bg = (0, 0, 0)

        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, font_thickness)

        base_padding = self.text_padding

        if position == 'bottom-right':
            x = w - text_w - base_padding
            y = h - base_padding - baseline - y_offset
        elif position == 'top-left':
            x = base_padding
            y = text_h + base_padding + y_offset
        elif position == 'top-right':
            x = w - text_w - base_padding
            y = text_h + base_padding + y_offset
        else:
            x = base_padding
            y = h - base_padding - baseline - y_offset

        bg_x1, bg_y1 = x - 5, y - text_h - 5
        bg_x2, bg_y2 = x + text_w + 5, y + baseline + 5

        bg_x1, bg_y1 = max(0, bg_x1), max(0, bg_y1)
        bg_x2, bg_y2 = min(w, bg_x2), min(h, bg_y2)

        if bg_x2 > bg_x1 and bg_y2 > bg_y1:
            roi = img_display[bg_y1:bg_y2, bg_x1:bg_x2]
            bg = np.full_like(roi, text_color_bg, dtype=np.uint8)
            blended = cv2.addWeighted(bg, 0.8, roi, 0.2, 0)
            img_display[bg_y1:bg_y2, bg_x1:bg_x2] = blended

        cv2.putText(img_display, text, (x, y), font, font_scale, text_color, font_thickness, cv2.LINE_AA)

    def _insert_text_at_position(self, img_display: np.ndarray, text: str, position: str, state: PreviewState = None) -> None:
        self._insert_text_at_position_with_offset(img_display, text, position, 0, state=state)

    def _text_stack(self, bottom_left: List[str] = None, bottom_right: List[str] = None,
                   top_left: List[str] = None, top_right: List[str] = None) -> List[tuple]:
        text_overlays = []

        if bottom_left:
            for text in bottom_left:
                text_overlays.append((str(text), 'bottom-left'))

        if bottom_right:
            for text in bottom_right:
                text_overlays.append((str(text), 'bottom-right'))

        if top_left:
            for text in top_left:
                text_overlays.append((str(text), 'top-left'))

        if top_right:
            for text in top_right:
                text_overlays.append((str(text), 'top-right'))

        return text_overlays
