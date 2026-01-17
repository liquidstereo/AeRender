import os, sys
import cv2
import numpy as np
import platform
import time
from os import PathLike
from typing import List, Union, Optional

try:
    import tkinter as tk
except ImportError:
    tk = None

try:
    import win32gui
    import win32con
except ImportError:
    win32gui = None
    win32con = None

def has_non_ascii_in_path(path_string) -> bool:
    return any(ord(char) > 127 for char in path_string)

def get_output_format(filename: str) -> str | None:
    parts = filename.split('.')
    if len(parts) >= 3:
        suffix = parts[-1]
        number_str = parts[-2]
        prefix = ".".join(parts[:-2])
        try:
            _ = int(number_str)
            padding = '#' * len(number_str)
            return f"{prefix}.{padding}.{suffix}"
        except ValueError:
            return None
    return None

def get_user_env_keycodes() -> dict:
    if platform.system() == "Windows":
        return {
            'LEFT_ARROW': 2424832,
            'RIGHT_ARROW': 2555904,
            'UP_ARROW': 2490368,
            'DOWN_ARROW': 2621440,
            'LEFT_ARROW_EX': 65361,
            'RIGHT_ARROW_EX': 65363,
            'UP_ARROW_EX': 65362,
            'DOWN_ARROW_EX': 65364,
            'NUMPAD_8': 56,
            'NUMPAD_2': 50,
            'NUMPAD_4': 52,
            'NUMPAD_6': 54,
            'NUMPAD_5': 53,
            'ZOOM_IN': 43,
            'ZOOM_OUT': 45,
            'PAGE_UP': 2162688,
            'PAGE_DOWN': 2228224,
        }
    elif platform.system() == "Darwin":
        return {
            'LEFT_ARROW': 65361,
            'RIGHT_ARROW': 65363,
            'UP_ARROW': 65362,
            'DOWN_ARROW': 65364,
            'LEFT_ARROW_EX': 65361,
            'RIGHT_ARROW_EX': 65363,
            'UP_ARROW_EX': 65362,
            'DOWN_ARROW_EX': 65364,
            'NUMPAD_8': 56,
            'NUMPAD_2': 50,
            'NUMPAD_4': 52,
            'NUMPAD_6': 54,
            'NUMPAD_5': 53,
            'ZOOM_IN': 43,
            'ZOOM_OUT': 45,
            'PAGE_UP': 65365,
            'PAGE_DOWN': 65366,
        }
    else:
        return {
            'LEFT_ARROW': 65361,
            'RIGHT_ARROW': 65363,
            'UP_ARROW': 65362,
            'DOWN_ARROW': 65364,
            'LEFT_ARROW_EX': 65361,
            'RIGHT_ARROW_EX': 65363,
            'UP_ARROW_EX': 65362,
            'DOWN_ARROW_EX': 65364,
            'NUMPAD_8': 56,
            'NUMPAD_2': 50,
            'NUMPAD_4': 52,
            'NUMPAD_6': 54,
            'NUMPAD_5': 53,
            'ZOOM_IN': 43,
            'ZOOM_OUT': 45,
            'PAGE_UP': 65365,
            'PAGE_DOWN': 65366,
        }

def calculate_pan_offset(pan_x: float, pan_y: float, zoom_w: int, zoom_h: int,
                        final_w: int, final_h: int) -> tuple[int, int]:
    max_offset_x = (zoom_w - final_w) // 2
    max_offset_y = (zoom_h - final_h) // 2

    offset_x = int(pan_x * max_offset_x)
    offset_y = int(pan_y * max_offset_y)

    start_x = max(0, min(zoom_w - final_w, max_offset_x + offset_x))
    start_y = max(0, min(zoom_h - final_h, max_offset_y + offset_y))

    return start_x, start_y

def insert_text(image: np.ndarray, text: str,
                font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=0.75,
                font_thickness=1, text_color=(255,255,255),
                text_color_bg=(0,0,0), background=True,
                padding_x=10, padding_y=10) -> tuple[int, int]:
    h, w = image.shape[:2]
    (text_w, text_h), base = cv2.getTextSize(text, font, font_scale, font_thickness)
    x, y = padding_x, h - padding_y - base

    if background:
        x1, y1 = x, y - text_h - base
        x2, y2 = x + text_w, y + base
        x1, y1 = max(0,x1), max(0,y1)
        x2, y2 = min(w,x2), min(h,y2)
        if x2 > x1 and y2 > y1:
            roi = image[y1:y2, x1:x2]
            bg = np.full_like(roi, text_color_bg, dtype=np.uint8)
            blended = cv2.addWeighted(bg, 0.8, roi, 0.2, 0)
            image[y1:y2, x1:x2] = blended

    cv2.putText(image, text, (x, y), font, font_scale,
                text_color, font_thickness, cv2.LINE_AA)
    return (text_w, text_h)

def center_window(window_name: str, img_width: int, img_height: int) -> None:
    if tk:
        try:
            root = tk.Tk()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root.destroy()

            center_x = (screen_width - img_width) // 2
            center_y = (screen_height - img_height) // 2

            cv2.moveWindow(window_name, center_x, center_y)
        except Exception:
            cv2.moveWindow(window_name, 100, 100)
    else:
        cv2.moveWindow(window_name, 100, 100)

def activate_window(window_name: str) -> None:
    try:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

        if platform.system() == 'Windows' and win32gui and win32con:
            try:
                def enum_windows_callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        window_text = win32gui.GetWindowText(hwnd)
                        if window_name in window_text:
                            windows.append(hwnd)
                    return True

                windows = []
                win32gui.EnumWindows(enum_windows_callback, windows)

                if windows:
                    hwnd = windows[0]
                    win32gui.SetForegroundWindow(hwnd)
                    win32gui.SetActiveWindow(hwnd)
                    win32gui.SetFocus(hwnd)

            except Exception:
                pass

    except Exception:
        pass

def load_image(image_path: str) -> tuple[np.ndarray, bool]:
    try:
        if not os.path.exists(image_path):
            return None, False
        if not os.access(image_path, os.R_OK):
            return None, False

        file_size = os.path.getsize(image_path)
        if file_size == 0:
            return None, False

        img_data = np.fromfile(image_path, np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        if img is None:
            return None, False
        return img, True
    except Exception as e:
        return None, False
