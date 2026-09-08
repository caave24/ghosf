# ghosf

> **ghosf does not just modify pixels. It treats previous moments in time as image layers.**

`ghosf` takes a video apart into every frame, lets the present carry selected moments from the past, then reassembles the video while preserving its timing.

## Core idea

```text
INPUT VIDEO
   ↓
EVERY FRAME
   ↓
CURRENT + SELECTED PREVIOUS MOMENTS
   ↓
TEMPORAL GHOST APPEARANCE + BLENDING
   ↓
EVERY FRAME REASSEMBLED
   ↓
OUTPUT VIDEO
```

The default temporal engine preserves:

- original frame rate
- frame count
- duration
- playback speed
- original audio when present

## Temporal controls

### Ghost History
How many previous moments remain visible.

### Ghost Frame Interval
How many original frames apart each ghost layer is.

```text
Interval 1: NOW, -1, -2, -3
Interval 2: NOW, -2, -4, -6
Interval 5: NOW, -5, -10, -15
```

This does **not** reduce output FPS.

## Ghost appearance

Older moments can gradually receive stronger visual treatment:

- contrast
- shadow depth
- highlight intensity
- brightness

## Blend modes

- **Normal** — transparent temporal layers
- **Screen** — light from previous moments accumulates
- **Additive** — stronger energetic trails

## End fade

Ghost layers can gradually fade out near the end using the configurable cubic-Bézier-inspired curve.

## Configuration Fingerprint

Every render receives a compact settings fingerprint in its filename:

```text
video_ghosf_<configuration-code>.mp4
```

The same settings generate the same code. Copy a code from one render and load it later to restore those settings.

## Output

- MP4 or AVI output
- Optional **Optimize output file** checkbox
- Optimization prioritizes preserving visual quality while avoiding unnecessary file size

## Cancellation

`CANCEL / ABORT` safely requests cancellation during extraction, frame processing, or rendering. Temporary working files are cleaned up and the original media is never modified.

## Current features

- Native PySide6 desktop GUI
- Drag-and-drop media
- Click-to-select media
- Project-local Python dependencies inside `.venv`
- FFmpeg executable supplied through `imageio-ffmpeg`
- Every-frame temporal processing
- Ghost frame interval
- Ghost history
- Ghost appearance controls
- Normal / Screen / Additive blending
- End fade and cubic Bézier curve
- Configuration fingerprints
- MP4 / AVI output
- Optional output optimization
- Original audio preservation
- Progress reporting
- Cancellation
- Output folder selection

## Setup

```bash
git clone <REPOSITORY_URL>
cd ghosf

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
python app.py
```

All Python dependencies install inside `.venv`. No global Python packages or `python3-tk` installation are required.

## VENV-FIRST

```text
Python packages → .venv
GUI toolkit     → .venv
FFmpeg binary   → managed by Python dependency
```

> **ghosf changes how much of the past remains visible in the present, not how quickly time plays.**
