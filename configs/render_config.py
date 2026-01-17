
import os
import json
from os import PathLike
from typing import List, Union
from dataclasses import dataclass

from configs import Msg

@dataclass
class RenderConfig:
    fpath: PathLike
    comp_name: Union[str, List[str]]
    output_dir: List[PathLike]
    start: Union[int, List[int]]
    end: Union[int, List[int]]
    workers: int
    per_task: int
    rs_template: str
    om_template: str
    ext: str
    verbose: str
    preview: bool
    logs: bool
    save_json: bool = False

    _calculated_workers: int = None
    _total_frames: int = None

    def __post_init__(self):
        from scripts import abs_path, make_dir

        if isinstance(self.fpath, str):
            self.fpath = abs_path(self.fpath)
        else:
            pass

        if isinstance(self.output_dir, str) and ',' in self.output_dir:
            self.output_dir = [os.path.abspath(path.strip()) for path in self.output_dir.split(',')]
        elif isinstance(self.output_dir, list):
            self.output_dir = [os.path.abspath(path) for path in self.output_dir]
        else:
            self.output_dir = [os.path.abspath(self.output_dir)]

        from scripts._ae_specifics import parse_multi_values, has_multiple_values

        if isinstance(self.comp_name, str) and has_multiple_values(self.comp_name):
            self.comp_name = parse_multi_values(self.comp_name)

        if isinstance(self.start, str) and has_multiple_values(self.start):
            start_values = parse_multi_values(self.start)
            self.start = [int(x) for x in start_values]
        elif isinstance(self.start, str):
            self.start = int(self.start)

        if isinstance(self.end, str) and has_multiple_values(self.end):
            end_values = parse_multi_values(self.end)
            self.end = [int(x) for x in end_values]
        elif isinstance(self.end, str):
            self.end = int(self.end)

        self._validate_frame_ranges()

    def _validate_frame_ranges(self):
        comp_count = 1 if isinstance(self.comp_name, str) else len(self.comp_name)

        if isinstance(self.start, list):
            if len(self.start) != comp_count:
                raise ValueError(f"Start frame count ({len(self.start)}) must match composition count ({comp_count})")

        if isinstance(self.end, list):
            if len(self.end) != comp_count:
                raise ValueError(f"End frame count ({len(self.end)}) must match composition count ({comp_count})")

        if isinstance(self.start, list) and isinstance(self.end, list):
            for i, (s, e) in enumerate(zip(self.start, self.end)):
                if s > e:
                    comp_name = self.comp_name[i] if isinstance(self.comp_name, list) else self.comp_name
                    raise ValueError(f"Start frame ({s}) must be <= end frame ({e}) for composition '{comp_name}'")
        elif isinstance(self.start, int) and isinstance(self.end, int):
            if self.start > self.end:
                raise ValueError(f"Start frame ({self.start}) must be <= end frame ({self.end})")

    def get_calculated_workers(self) -> int:
        if self._calculated_workers is None:
            if self.workers == 0:
                from scripts._get_usable_workers import get_usable_workers
                self._calculated_workers = get_usable_workers()
            else:
                total_frames = self.get_total_frames()
                self._calculated_workers = min(self.workers, total_frames)
        return self._calculated_workers

    def get_total_frames(self) -> int:
        if self._total_frames is None:
            from scripts import get_composition_frames

            comp_count = 1 if isinstance(self.comp_name, str) else len(self.comp_name)
            total = 0
            for i in range(comp_count):
                start_frame, end_frame = get_composition_frames(self, i)
                total += (end_frame - start_frame + 1)
            self._total_frames = total
        return self._total_frames

    def create_for_composition(self, comp_name: str, comp_index: int, is_multi: bool = False):
        from scripts import get_composition_frames

        start_frame, end_frame = get_composition_frames(self, comp_index)

        if isinstance(self.output_dir, list) and len(self.output_dir) > comp_index:
            output_subdir = self.output_dir[comp_index]
        elif isinstance(self.output_dir, list) and len(self.output_dir) > 0:
            output_subdir = self.output_dir[0]
        else:
            output_subdir = str(self.output_dir)

        return RenderConfig(
            fpath=self.fpath,
            comp_name=comp_name,
            output_dir=[output_subdir],
            start=start_frame,
            end=end_frame,
            workers=self.workers,
            per_task=self.per_task,
            rs_template=self.rs_template,
            om_template=self.om_template,
            ext=self.ext,
            verbose=self.verbose,
            preview=self.preview,
            logs=self.logs,
            save_json=self.save_json
        )

    def to_dict(self) -> dict:
        return {
            'fpath': str(self.fpath),
            'comp_name': self.comp_name,
            'output_dir': [str(path) for path in self.output_dir] if isinstance(self.output_dir, list) else [str(self.output_dir)],
            'start': self.start,
            'end': self.end,
            'workers': self.workers,
            'per_task': self.per_task,
            'rs_template': self.rs_template,
            'om_template': self.om_template,
            'ext': self.ext,
            'verbose': self.verbose,
            'preview': self.preview,
            'logs': self.logs,
            'save_json': self.save_json,
            'calculated_workers': self._calculated_workers,
            'total_frames': self._total_frames
        }

    def save_task_json(self, output_dir: str, log_filename: str) -> str:
        json_filename = f"{log_filename}_task.json"
        json_path = os.path.join(output_dir, json_filename)

        os.makedirs(output_dir, exist_ok=True)

        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return json_path
        except Exception as e:
            Msg.Warning(f"Failed to save config JSON: {e}")
            return ""
