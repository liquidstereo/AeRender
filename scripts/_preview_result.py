import os, sys
import cv2
import numpy as np
import threading
from os import PathLike
from typing import List, Union

from scripts._common import list_files_in_dir
from configs import Msg

def has_non_ascii_in_path(path_string) -> bool:
    '''
    ◦ Checks if a given file path string contains non-ASCII characters.

    Args:
        path_string (str): The file path string to check.

    Returns:
        bool: True if non-ASCII characters are found, False otherwise.

    Raises:
        None

    Examples:
        has_non_ascii_in_path("C:/Users/user/document.txt") # -> False
        has_non_ascii_in_path("D:/사진/image.jpg") # -> True
    '''
    return any(ord(char) > 127 for char in path_string)

def get_output_format(filename: str) -> str | None:
    '''
    ◦ Converts filenames from 'prefix.number.suffix' to 'prefix.####.suffix'.

    Args:
        filename (str): The filename to convert.

    Returns:
        str | None: Formatted string or None if unmatched.

    Raises:
        None

    Examples:
        get_output_format('render.0000.png') # -> 'render.####.png'
    '''
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

def insert_text(image: np.ndarray, text: str,
                font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=0.75,
                font_thickness=1, text_color=(255,255,255),
                text_color_bg=(0,0,0), background=True,
                padding_x=10, padding_y=10) -> tuple[int, int]:
    '''
    ◦ Insert text into image at bottom-left with padding.

    Args:
        image: image to draw
        text: text string
        font: font type
        font_scale: font size
        font_thickness: text thickness
        text_color: font color
        text_color_bg: background color
        background: show background
        padding_x: horizontal padding
        padding_y: vertical padding

    Returns:
        tuple: (text_width, text_height)

    Raise:
        None
    '''
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

def resize_image(image: np.ndarray,
                 width: int = None,
                 height: int = None,
                 inter=cv2.INTER_AREA) -> np.ndarray:
    '''
    ◦ Resize image maintaining aspect ratio.

    Args:
        image: input image
        width: desired width
        height: desired height
        inter: interpolation method

    Returns:
        np.ndarray

    Raise:
        None
    '''
    h, w = image.shape[:2]
    if width is None and height is None:
        return image
    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))
    return cv2.resize(image, dim, interpolation=inter)

def load_image(image_path: str) -> tuple[np.ndarray, bool]:
    '''
    ◦ Safely load image with error handling, supporting non-ASCII paths.

    Args:
        image_path (str): Image file path.

    Returns:
        tuple: (image_data, success)

    Raises:
        None

    Examples:
        load_image('image.jpg')
    '''
    try:
        if not os.path.exists(image_path):
            Msg.Error(f'FILE NOT FOUND: {image_path}')
            return None, False
        if not os.access(image_path, os.R_OK):
            Msg.Error(f'FILE NOT READABLE: {image_path}')
            return None, False

        # Read file as bytes and then decode for non-ASCII path support
        img_data = np.fromfile(image_path, np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        if img is None:
            size = os.path.getsize(image_path)
            ext = os.path.splitext(image_path)[1]
            Msg.Error(f'CANNOT LOAD: {image_path} SIZE:{size} EXT:{ext}')
            return None, False
        return img, True
    except Exception as e:
        Msg.Error(f'ERROR LOADING {image_path}: {e}')
        return None, False

def preview_result(result_fname_list: List[str],
                   result_img_list: List[Union[str, PathLike]],
                   resize: bool=True) -> None:
    '''
    ◦ Execute image preview with OpenCV.

    Args:
        result_fname_list: list of filenames
        result_img_list: list of image paths
        resize: resize toggle

    Returns:
        None

    Raise:
        None

    Examples:
        preview_result(fname_list, img_list, resize=True)
    '''
    stop_event = threading.Event()
    blink_thread = threading.Thread(
        target = Msg.Blink,
        args = ('LOADING RESULT PREVIEW. PLEASE WAIT⋯',),
        kwargs = {'stop_event': stop_event, 'clear_on_finish': True,
                'color': 'Dim'}
    )
    blink_thread.daemon = True
    blink_thread.start()

    if not result_img_list:
        stop_event.set()
        blink_thread.join()
        Msg.Error('NO VALID IMAGES FOUND TO PREVIEW.')
        return

    file_extension = os.path.splitext(result_img_list[0])[1].lower()
    supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff']

    if file_extension not in supported_formats:
        stop_event.set()
        blink_thread.join()
        ext_name = file_extension.replace('.', '').upper()
        available_formats = ', '.join([fmt.lstrip('.') for fmt in supported_formats])
        m = (
            f'\"{ext_name}\" preview not supported.\n'
            f'Supported formats: {available_formats}.\n'
            f'Preview skipped.'
        )
        Msg.Red(f'{m.upper()}')
        print(f'-')
        return



    valid_idx = [i for i, p in enumerate(result_img_list)
                 if load_image(p)[1]]
    if not valid_idx:
        Msg.Error('NO VALID IMAGES FOUND TO PREVIEW.')
        return

    prefix = get_output_format(result_img_list[0]).replace(os.sep, '/')
    play_msg = (f'Found {len(valid_idx)} valid of '
                f'{len(result_img_list)} images. '
                f'Press ESC to exit.').upper()

    blink_stopped = False
    RESIZE_VALUE = 0.5    # ← PREVIEW RESIZE VALUE

    while True:
        for i in valid_idx:
            img, ok = load_image(result_img_list[i])
            if not ok: continue
            try:
                h, w = img.shape[:2]
                if resize:
                    img = resize_image(img, width=int(w * RESIZE_VALUE))    # ← RESIZE PREVIEW
                insert_text(img, result_fname_list[i])
                title = f'{prefix} ({w}px, {h}px)'
                # Convert title to bytes using utf-8, then decode using system's filesystem encoding
                # This often resolves non-ASCII character issues in OpenCV window titles on Windows
                try:
                    encoded_title = title.encode('utf-8').decode(sys.getfilesystemencoding())    # ← UTF-8 ENCORD
                except (UnicodeEncodeError, UnicodeDecodeError):
                    encoded_title = title # Fallback if encoding fails
                cv2.imshow(encoded_title, img)
                cv2.setWindowProperty(title, cv2.WND_PROP_TOPMOST, 1)
                if not blink_stopped:
                    stop_event.set()
                    blink_thread.join()
                    blink_stopped = True
                    Msg.Green(play_msg.upper(), flush=True)
                key = cv2.waitKey(1) & 0xFF
                if key == 27: break
                if cv2.getWindowProperty(title,
                                         cv2.WND_PROP_VISIBLE) <= 0:
                    break
            except Exception as e:
                Msg.Error(f'ERROR WITH IMAGE {result_fname_list[i]}: {e}')
        else:
            continue
        break

    cv2.destroyAllWindows()
    if not blink_stopped:
        stop_event.set()
        blink_thread.join()
    print('\033[K', end='', flush=True)

def main():
    '''
    ◦ Main function for testing.
    '''
    try:
        img_list = list_files_in_dir(r'__DIR__', pat='png')
        if not img_list:
            return
        fname_list = [os.path.basename(f) for f in img_list]
        preview_result(fname_list, img_list, resize=True)
    except Exception as e:
        Msg.Error(f'Error in main: {e}')

if __name__ == '__main__':
    main()
