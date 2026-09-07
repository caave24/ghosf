import json
import subprocess
import tempfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from core.curves import end_fade_strength
from core.ffmpeg import ffmpeg_exe
from effects.ghost import compose


@dataclass
class Settings:
    frame_interval: int = 80
    ghost_history: int = 10
    max_pixel_size: int = 16
    pixel_curve: str = "memory"
    blend_mode: str = "screen"
    end_fade_enabled: bool = True
    end_fade_frames: int = 20
    fade_bezier: tuple = (0.17, 0.67, 0.77, 0.42)


class GhosfProcessor:
    def __init__(self, input_path, output_dir, settings, emit):
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.settings = settings
        self.emit = emit
        self.ffmpeg = ffmpeg_exe()

    def progress(self, percent, message):
        self.emit(("progress", float(percent), message))

    def run(self):
        if not self.input_path.exists():
            raise RuntimeError("Input media does not exist.")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        info = self._probe_media()

        output_path = self.output_dir / f"{self.input_path.stem}_ghosf.mp4"

        with tempfile.TemporaryDirectory(prefix="ghosf_") as temporary:
            temporary = Path(temporary)
            extracted = temporary / "frames"
            processed = temporary / "processed"
            extracted.mkdir()
            processed.mkdir()

            self._extract_frames(extracted)
            frames = sorted(extracted.glob("frame_*.png"))

            if not frames:
                raise RuntimeError("No frames were extracted from the media.")

            self._process_frames(frames, processed)
            self._render_video(processed, output_path, info)

        return output_path

    def _probe_media(self):
        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-i", str(self.input_path),
            "-f", "null",
            "-",
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        stderr = result.stderr

        has_audio = "Audio:" in stderr
        fps = 30.0

        for line in stderr.splitlines():
            if "Video:" in line and " fps" in line:
                try:
                    before = line.split(" fps", 1)[0]
                    fps = float(before.rsplit(",", 1)[-1].strip())
                    break
                except Exception:
                    pass

        return {"fps": fps, "has_audio": has_audio}

    def _extract_frames(self, frame_dir):
        interval = max(1, self.settings.frame_interval)
        pattern = frame_dir / "frame_%06d.png"

        # This is the discussed temporal sampling operation:
        # select every Nth frame, producing the temporal source layers.
        vf = f"select='not(mod(n\\,{interval}))'"

        cmd = [
            self.ffmpeg,
            "-y",
            "-i", str(self.input_path),
            "-vf", vf,
            "-vsync", "0",
            "-compression_level", "3",
            str(pattern),
        ]

        self.progress(0, "Extracting temporal samples…")
        self._run(cmd)
        self.progress(20, "Temporal samples extracted.")

    def _process_frames(self, frame_paths, processed_dir):
        total = len(frame_paths)
        history = deque(maxlen=max(1, self.settings.ghost_history))

        for index, path in enumerate(frame_paths):
            with Image.open(path) as opened:
                current = opened.convert("RGBA").copy()

            fade_strength = 1.0
            if self.settings.end_fade_enabled:
                fade_strength = end_fade_strength(
                    index,
                    total,
                    self.settings.end_fade_frames,
                    self.settings.fade_bezier,
                )

            result = compose(
                current=current,
                history_layers=list(history),
                settings=self.settings,
                fade_strength=fade_strength,
            )

            result.save(processed_dir / f"frame_{index + 1:06d}.png")
            history.append(current)

            percent = 20 + ((index + 1) / total) * 60
            self.progress(
                percent,
                f"Building temporal layers… {index + 1}/{total}",
            )

    def _render_video(self, processed_dir, output_path, info):
        fps = max(
            0.001,
            info["fps"] / max(1, self.settings.frame_interval),
        )

        pattern = processed_dir / "frame_%06d.png"

        cmd = [
            self.ffmpeg,
            "-y",
            "-framerate", f"{fps:.12g}",
            "-i", str(pattern),
        ]

        if info["has_audio"]:
            cmd += [
                "-i", str(self.input_path),
                "-map", "0:v:0",
                "-map", "1:a?",
                "-c:a", "aac",
                "-b:a", "192k",
            ]

        cmd += [
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "17",
            "-shortest",
            str(output_path),
        ]

        self.progress(80, "Rendering ghosf video…")
        self._run(cmd)
        self.progress(100, "Rendering complete.")

    def _run(self, cmd):
        process = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        if process.returncode != 0:
            tail = process.stderr[-5000:]
            raise RuntimeError(f"FFmpeg failed:\n\n{tail}")
