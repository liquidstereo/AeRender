import os
import sys
import cv2
import numpy as np
import threading
import time
from os import PathLike
from typing import List, Union, Optional

from configs import Msg
from configs.defaults import RESIZE_PREVIEW

from scripts._common import list_files_in_dir, flush_lines

from ._preview_utils import (
    has_non_ascii_in_path, get_output_format, get_user_env_keycodes,
    calculate_pan_offset, insert_text, center_window, activate_window, load_image
)
from ._preview_state import PreviewState
from ._input_handler import InputHandler
from ._preview_renderer import PreviewRenderer

class ImageCache:
    def __init__(self, max_cache_size: int = 5):
        self.cache = {}
        self.max_size = max_cache_size
        self.access_order = []

    def get(self, path: str) -> Optional[np.ndarray]:
        if path in self.cache:
            self.access_order.remove(path)
            self.access_order.append(path)
            return self.cache[path]

        img, success = load_image(path)
        if success and img is not None:
            if len(self.cache) >= self.max_size:
                oldest = self.access_order.pop(0)
                del self.cache[oldest]

            self.cache[path] = img
            self.access_order.append(path)
            return img
        return None

class PreviewApp:

    def __init__(self, img_list: List[Union[str, PathLike]],
                 resize: bool = True,
                 resize_value: float = 0.85,
                 show_controls_msg: bool = True,
                 target_fps: float = 30.0,
                 cache_size: int = 7,
                 set_text: tuple = None,
                 text_padding: int = 45,
                 text_line_spacing: int = 35,
                 font_size: float = 0.75,
                 key_preset: str = 'DEFAULT',
                 window_title: str = None):
        self.img_list = img_list
        self.result_fname_list = [os.path.basename(path) for path in img_list]
        self.resize = resize
        self.stop_event = threading.Event()
        self.blink_thread = None
        self.valid_idx = []
        self.image_cache = None
        self.preview_start_msg = ''
        self.state = PreviewState(
            zoom_level=1.0, pan_x=0.0, pan_y=0.0, pan_step=0.1
        )
        self.resize_value = max(0.1, min(1.0, resize_value))
        self._default_resize_value = self.resize_value

        self.show_controls_msg = show_controls_msg
        self.target_fps = max(1.0, min(120.0, target_fps))
        self.cache_size = max(1, min(20, cache_size))
        self.input_handler = InputHandler(key_preset=key_preset)
        self.renderer = PreviewRenderer(
            resize=resize,
            resize_value=self.resize_value,
            text_padding=max(10, text_padding),
            text_line_spacing=max(10, text_line_spacing),
            font_size=max(0.3, min(2.0, font_size)),
            custom_window_title=window_title,
            set_text=set_text,
            fixed_title=None
        )

    def _start_loading_indicator(self) -> None:
        self.blink_thread = threading.Thread(
            target=Msg.Blink,
            args=('',),
            kwargs={'stop_event': self.stop_event, 'clear_on_finish': True, 'color': 'Dim'}
        )
        self.blink_thread.daemon = True
        self.blink_thread.start()

    def _check_format(self) -> bool:
        if not self.img_list:
            return False

        test_file = self.img_list[0]
        file_extension = os.path.splitext(test_file)[1].lower()

        common_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff']

        if file_extension in common_formats:
            return True

        try:
            test_img = cv2.imread(test_file, cv2.IMREAD_UNCHANGED)
            if test_img is not None:
                return True
        except Exception:
            pass

        ext_name = file_extension.replace('.', '').upper()
        all_formats = ['.png', '.jpg', '.jpeg', '.jpe', '.bmp', '.dib',
                      '.tif', '.tiff', '.webp', '.jp2', '.pbm', '.pgm',
                      '.ppm', '.pnm', '.sr', '.ras', '.tga', '.exr']
        available_formats = ', '.join([fmt.lstrip('.').upper()
                                     for fmt in all_formats])

        err_msg = (
            f'\"{ext_name}\" format not supported by OpenCV.\n'
            f'Common formats: PNG, JPG, BMP, TIF, WEBP, etc.\n'
            f'Preview skipped.\n'
        )
        Msg.Red(err_msg)
        self.stop_event.set()
        if self.blink_thread:
            self.blink_thread.join()
        return False

    def _validate_images(self) -> bool:

        err_msg = 'No Valid Images Found To Preview.'

        if not self.img_list:
            Msg.Error(err_msg)
            self.stop_event.set()
            if self.blink_thread:
                self.blink_thread.join()
            return False

        self.image_cache = ImageCache(max_cache_size=self.cache_size)

        self.valid_idx = []
        for i, p in enumerate(self.img_list):
            if os.path.exists(p) and os.access(p, os.R_OK) and os.path.getsize(p) > 0:
                self.valid_idx.append(i)

        if not self.valid_idx:
            Msg.Error(err_msg)
            self.stop_event.set()
            if self.blink_thread:
                self.blink_thread.join()
            return False

        return True

    def _prepare_preview_start_msg(self) -> None:

        base_msg = (
            f'Result.Preview: Found {len(self.valid_idx)} '
            f'valid of {len(self.img_list)} images.'
        )

        if self.show_controls_msg:
            controls_text = self.input_handler.get_controls_text()
            self.preview_start_msg = f'{base_msg}\n{controls_text}'.upper()
            print('-')
        else:
            self.preview_start_msg = base_msg.upper()
            print('-')

    def _execute_main_loop(self) -> None:
        blink_stopped = False
        self.state.current_index = 0
        self.state.paused = False
        target_frame_time = 1.0 / self.target_fps
        fps_last_frame_time = time.time()
        window_created = False
        current_window_name = None

        while True:
            frame_start_time = time.time()

            if self.state.is_multi_comp:
                current_comp_data = self.state.get_current_comp_data()
                if not current_comp_data:
                    continue

                current_img_list = current_comp_data.get('fnames', [])
                current_result_fnames = current_comp_data.get('images', [])

                if not current_img_list:
                    continue

                valid_idx_len = len(current_img_list)
            else:
                current_img_list = self.img_list
                current_result_fnames = self.result_fname_list
                valid_idx_len = len(self.valid_idx)

            if not self.state.paused:
                self.state.current_index = (self.state.current_index + 1) % valid_idx_len

            if self.state.is_multi_comp:
                current_img_index = self.state.current_index
                if current_img_index >= len(current_img_list):
                    continue
                current_img_path = current_img_list[current_img_index]
                current_fname = current_result_fnames[current_img_index] if current_img_index < len(current_result_fnames) else ""
            else:
                i = self.valid_idx[self.state.current_index]
                current_img_path = self.img_list[i]
                current_fname = self.result_fname_list[i]

            img = self.image_cache.get(current_img_path)
            if img is None:
                continue

            try:
                current_fps, fps_last_frame_time = self._calculate_fps(fps_last_frame_time)

                img_display, encoded_title = self.renderer.render_frame(
                    img, current_fname, valid_idx_len,
                    self.state, current_fps
                )

                if not window_created:
                    cv2.imshow(encoded_title, img_display)
                    current_window_name = encoded_title
                    window_created = True
                else:
                    cv2.imshow(current_window_name, img_display)

                blink_stopped = self._setup_preview_window(current_window_name, img_display, blink_stopped)

                if not self.state.paused:
                    processing_time = time.time() - frame_start_time
                    wait_time = max(1, int((target_frame_time - processing_time) * 1000))
                else:
                    wait_time = 50

                key_raw = cv2.waitKeyEx(wait_time)
                should_exit = self._handle_keyboard_input(
                    key_raw, valid_idx_len
                )

                if should_exit and self.show_controls_msg:
                    flush_lines(3)
                    break

                if window_created and cv2.getWindowProperty(current_window_name, cv2.WND_PROP_VISIBLE) <= 0:
                    flush_lines(3)
                    break

            except Exception as e:
                Msg.Error(f'Error With Image {self.result_fname_list[i]}: {e}')
                continue

        cv2.destroyAllWindows()

    def _calculate_fps(self, fps_last_frame_time: float) -> tuple[float, float]:
        current_time = time.time()
        if not self.state.paused:
            return round(1.0 / max(0.001, current_time - fps_last_frame_time), 1), current_time
        return 30.0, fps_last_frame_time

    def _setup_preview_window(self, window_name: str, img_display: np.ndarray, blink_stopped: bool) -> bool:
        if not blink_stopped and window_name:
            try:
                img_h, img_w = img_display.shape[:2]
                center_window(window_name, img_w, img_h)
                activate_window(window_name)
                self.stop_event.set()
                if self.blink_thread and self.blink_thread.is_alive():
                    self.blink_thread.join(timeout=0.1)
                Msg.Green(self.preview_start_msg.upper(), flush=True)
                return True
            except Exception:
                pass
        return blink_stopped

    def _handle_keyboard_input(self, key_raw: int, valid_idx_len: int) -> bool:
        action = self.input_handler.check_key_action(key_raw)

        if action == 'exit':
            return True
        elif action == 'pause':
            self.state.paused = not self.state.paused
        elif action == 'prev':
            self.state.paused = True
            self.state.current_index = (self.state.current_index - 1) % valid_idx_len
        elif action == 'next':
            self.state.paused = True
            self.state.current_index = (self.state.current_index + 1) % valid_idx_len
        elif action == 'first':
            self.state.paused = True
            self.state.current_index = 0
        elif action == 'last':
            self.state.paused = True
            self.state.current_index = valid_idx_len - 1
        elif action == 'zoom_in':
            self.state.update_zoom('in')
        elif action == 'zoom_out':
            self.state.update_zoom('out')
        elif action == 'reset':
            self.state.reset_to_defaults()
        elif action in ['pan_up', 'pan_down', 'pan_left', 'pan_right', 'pan_reset']:
            if self.state.zoom_level > 1.0:
                self.state.update_pan(action)
        elif action == 'prev_comp':
            if self.state.is_multi_comp:
                self.state.prev_comp()
                self.state.paused = False
        elif action == 'next_comp':
            if self.state.is_multi_comp:
                self.state.next_comp()
                self.state.paused = False

        return False

    def _cleanup(self) -> None:
        try:
            if not self.stop_event.is_set():
                self.stop_event.set()
            if self.blink_thread and self.blink_thread.is_alive():
                self.blink_thread.join(timeout=0.5)

            cv2.destroyAllWindows()

            cv2.waitKeyEx(1)

        except Exception:
            pass

    def run(self) -> None:
        try:
            self._start_loading_indicator()

            if not self._check_format():
                return

            if not self._validate_images():
                return

            self._prepare_preview_start_msg()
            self._execute_main_loop()

        finally:
            self._cleanup()

def preview_result(img_list=None, multi_comp_data=None) -> None:

    title = 'Result Preview: {results_dir} - {format} ({width} X {height})'

    resize = True
    resize_value = RESIZE_PREVIEW
    show_controls_msg = True
    target_fps = 30.0
    cache_size = 10
    font_size = 0.75
    text_padding = 20
    text_line_spacing = 34

    preview_key_preset = 'ARROW_DEFAULT'

    texts = [
        ('{filename}', 'bottom-left'),
        ('FRAME: {frame_index}', 'bottom-right'),
        ('FPS: {fps}', 'bottom-right'),
    ]

    if multi_comp_data:
        texts.append(('{comp_info}', 'top-right'))

    if multi_comp_data:
        comp_names = multi_comp_data.get('comp_names', [])
        comp_data_list = multi_comp_data.get('comp_data', [])

        if not comp_names or not comp_data_list:
            Msg.Error("Invalid multi-composition data provided.")
            return

        if comp_data_list and comp_data_list[0]:
            img_list = comp_data_list[0].get('fnames', [])
        else:
            Msg.Error("No valid composition data found.")
            return
    elif img_list:
        comp_names = []
        comp_data_list = []
    else:
        Msg.Error("Either img_list or multi_comp_data must be provided.")
        return

    previewer = PreviewApp(
        img_list, resize,
        resize_value=resize_value,
        show_controls_msg=show_controls_msg,
        target_fps=target_fps,
        cache_size=cache_size,
        set_text=texts,
        text_padding=text_padding,
        text_line_spacing=text_line_spacing,
        font_size=font_size,
        key_preset=preview_key_preset,
        window_title=title
    )

    if multi_comp_data:
        previewer.state.setup_multi_comp(comp_names, comp_data_list)

    previewer.run()

def main():
    try:
        img_list = list_files_in_dir(r'__DIR__', pat='png')
        if not img_list:
            Msg.Error("테스트용 PNG 파일을 찾을 수 없습니다.")
            Msg.Info("__DIR__ 경로에 PNG 파일이 있는지 확인하세요.")
            return
        preview_result(img_list)
    except Exception as e:
        Msg.Error(f'Error in main: {e}')

if __name__ == '__main__':
    main()
