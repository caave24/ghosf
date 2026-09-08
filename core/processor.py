import subprocess
import tempfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from core.config_code import short_fingerprint
from core.curves import end_fade_strength
from core.ffmpeg import ffmpeg_exe
from effects.ghost import compose


class ProcessingCancelled(Exception):
    pass


@dataclass
class Settings:
    ghost_frame_interval: int = 1
    ghost_history: int = 10
    blend_mode: str = "screen"
    end_fade_enabled: bool = True
    end_fade_frames: int = 20
    fade_bezier: tuple = (0.17, 0.67, 0.77, 0.42)
    ghost_contrast: int = 20
    shadow_depth: int = 15
    highlight_intensity: int = 10
    ghost_brightness: int = 0
    optimize_output: bool = False
    output_format: str = "mp4"


class GhosfProcessor:
    def __init__(self, input_path, output_dir, settings, emit, cancel_event=None):
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.emit = emit
        self.cancel_event = cancel_event
        self.ffmpeg = ffmpeg_exe()
        self.active_process = None

    def progress(self, percent, message):
        self.emit(("progress", float(percent), message))

    def _cancelled(self):
        return self.cancel_event is not None and self.cancel_event.is_set()

    def _check_cancelled(self):
        if self._cancelled():
            raise ProcessingCancelled("Creation cancelled.")

    def cancel(self):
        if self.cancel_event is not None:
            self.cancel_event.set()
        if self.active_process and self.active_process.poll() is None:
            self.active_process.terminate()

    def run(self):
        if not self.input_path.exists():
            raise RuntimeError("Input media does not exist.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        info = self._probe_media()
        fingerprint = short_fingerprint(self.settings)
        extension = self.settings.output_format.lower()
        output_path = self.output_dir / f"{self.input_path.stem}_ghosf_{fingerprint}.{extension}"

        with tempfile.TemporaryDirectory(prefix="ghosf_") as temporary:
            temporary = Path(temporary)
            extracted = temporary / "frames"
            processed = temporary / "processed"
            extracted.mkdir(); processed.mkdir()
            self._extract_frames(extracted)
            frames = sorted(extracted.glob("frame_*.png"))
            if not frames:
                raise RuntimeError("No frames were extracted from the media.")
            self._process_frames(frames, processed)
            self._render_video(processed, output_path, info)

        self._check_cancelled()
        return output_path

    def _probe_media(self):
        cmd = [self.ffmpeg, "-hide_banner", "-i", str(self.input_path), "-f", "null", "-"]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        stderr = result.stderr
        has_audio = "Audio:" in stderr
        fps = 30.0
        for line in stderr.splitlines():
            if "Video:" in line and " fps" in line:
                try:
                    fps = float(line.split(" fps", 1)[0].rsplit(",", 1)[-1].strip()); break
                except Exception:
                    pass
        return {"fps": fps, "has_audio": has_audio}

    def _extract_frames(self, frame_dir):
        pattern = frame_dir / "frame_%06d.png"
        cmd = [self.ffmpeg, "-y", "-i", str(self.input_path), "-vsync", "0", "-compression_level", "3", str(pattern)]
        self.progress(0, "Extracting every frame…")
        self._run(cmd)
        self.progress(20, "Frames extracted. Preserving original timing.")

    def _process_frames(self, frame_paths, processed_dir):
        total = len(frame_paths)
        interval = max(1, self.settings.ghost_frame_interval)
        max_history = max(1, self.settings.ghost_history * interval)
        history = deque(maxlen=max_history)
        for index, path in enumerate(frame_paths):
            self._check_cancelled()
            with Image.open(path) as opened:
                current = opened.convert("RGBA").copy()
            selected = []
            history_list = list(history)
            for ghost_number in range(1, self.settings.ghost_history + 1):
                offset = ghost_number * interval
                if len(history_list) >= offset:
                    selected.append(history_list[-offset])
            fade_strength = 1.0
            if self.settings.end_fade_enabled:
                fade_strength = end_fade_strength(index, total, self.settings.end_fade_frames, self.settings.fade_bezier)
            result = compose(current, selected, self.settings, fade_strength)
            result.save(processed_dir / f"frame_{index + 1:06d}.png")
            history.append(current)
            self.progress(20 + ((index + 1) / total) * 60, f"Building temporal layers… {index + 1}/{total}")

    def _render_video(self, processed_dir, output_path, info):
        pattern = processed_dir / "frame_%06d.png"
        cmd = [self.ffmpeg, "-y", "-framerate", f"{max(0.001, info['fps']):.12g}", "-i", str(pattern)]
        if info["has_audio"]:
            cmd += ["-i", str(self.input_path), "-map", "0:v:0", "-map", "1:a?"]
        if self.settings.output_format.lower() == "avi":
            cmd += ["-c:v", "mpeg4", "-q:v", "2", "-c:a", "mp3", "-shortest"]
        else:
            crf = "18" if self.settings.optimize_output else "17"
            preset = "slow" if self.settings.optimize_output else "medium"
            cmd += ["-c:v", "libx264", "-preset", preset, "-pix_fmt", "yuv420p", "-crf", crf]
            if info["has_audio"]:
                cmd += ["-c:a", "aac", "-b:a", "192k"]
            cmd += ["-movflags", "+faststart", "-shortest"]
        # FFmpeg requires the output file as the final command argument.
        cmd += [str(output_path)]
        self.progress(80, "Rendering ghosf video…")
        self._run(cmd)
        self.progress(100, "Rendering complete.")

    def _run(self, cmd):
        self._check_cancelled()
        self.active_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        _, stderr = self.active_process.communicate()
        code = self.active_process.returncode
        self.active_process = None
        if self._cancelled():
            raise ProcessingCancelled("Creation cancelled.")
        if code != 0:
            raise RuntimeError(f"FFmpeg failed:\n\n{stderr[-5000:]}")
