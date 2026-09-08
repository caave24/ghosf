<img width="802" height="951" alt="image" src="https://github.com/user-attachments/assets/14ef420b-58c2-4ea4-964e-4303e11d0973" />


# ghosf

> **ghosf treats previous moments in time as image layers.**

## Download & Run

```bash
git clone <REPOSITORY_URL>
cd ghosf

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
python app.py
```

`ghosf` uses a project-local `.venv`. No Python packages need to be installed globally.

---

## What it does

```text
VIDEO
  ↓
DECODE EVERY FRAME
  ↓
CURRENT FRAME + PREVIOUS MOMENTS
  ↓
TEMPORAL GHOSTING / PROCESSING
  ↓
REASSEMBLE VIDEO
```

The video keeps its original:

- FPS
- duration
- frame count
- playback speed
- audio, when available

`ghosf` changes how much of the past remains visible in the present.

---

## Temporal Ghosts

Each output frame can contain the current moment plus earlier moments.

```text
CURRENT

NOW      ████████████
-1       ▓▓▓▓▓▓▓▓▓
-2       ▒▒▒▒▒▒▒
-3       ░░░░░░
```

### Ghost History

How many previous moments remain visible.

### Ghost Frame Interval

How far apart those moments are.

```text
Interval 1

F10 → F9 → F8 → F7
```

```text
Interval 2

F10 → F8 → F6 → F4
```

This affects **ghost layers only**. Every original video frame remains in the output.

---

## Ghost Appearance

Previous moments can change gradually with age:

- Contrast
- Shadow Depth
- Highlight Intensity
- Brightness

```text
NOW       → natural
RECENT    → subtle treatment
OLDER     → stronger treatment
OLDEST    → strongest treatment
```

---

## Blend Modes

**Normal** — transparent temporal layers.

**Screen** — light from previous moments accumulates.

**Additive** — stronger, energetic temporal trails.

---

## Other Features

- Drag and drop media
- Click to select media
- End fade with cubic-Bézier control
- Configuration fingerprints
- Copy/load render settings
- MP4 output
- AVI output
- Optional output optimization
- Output folder selection
- Progress reporting
- Cancel / Abort processing

### Configuration Fingerprints

Render settings can be represented by a compact code:

```text
video_ghosf_F3FpdGGasd.mp4
```

Copy or share the code, then paste it back into `ghosf` to restore the same settings.

---

## Philosophy

```text
PAST                                      NOW

▓▓▓▓▓▓▓▓▓▓ → ▒▒▒▒▒▒▒▒▒▒ → ░░░░░░░░ → ███████████

TIME ───────────────────────────────────────────────────→
```

Video normally treats frames as separate moments.

**ghosf lets previous moments remain visible.**
