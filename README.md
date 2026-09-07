# GHOSF

> **GHOSF does not just modify pixels. It treats previous moments in time as image layers.**

GHOSF is an experimental Python + FFmpeg temporal video processor.

The present remains sharp. Previous moments remain visible as temporal layers that can fade, pixelate, drift, transform, and decay.

---

# Temporal Pixel Decay

The further back a frame exists in time, the less spatial information it retains.

The past is not simply transparent.

It becomes increasingly low-resolution.

```text id="ghosf-oldest-current"
OLDEST                                      CURRENT

▓▓▓▓▓▓▓▓▓▓      ▒▒▒▒▒▒▒▒▒▒      ░░░░░░░░      ███████████
▓▓▓▓▓▓▓▓▓▓  →   ▒▒▒▒▒▒▒▒▒▒  →   ░░░░░░░░  →   ███████████

heavily         pixelated         slightly        sharp
pixelated                         pixelated
```

```text id="ghosf-time-resolution"
TIME ───────────────────────────────→ NOW

t-10     t-8      t-6      t-4      t-2      NOW
████     ▓▓▓▓     ▒▒▒▒     ░░░░     ░░░░     ████████

8 px     6 px     4 px     2 px     1 px     FULL RES
```

```text id="ghosf-information"
PAST                                   PRESENT

LOW INFORMATION                       HIGH INFORMATION

▓▓▓▓▓▓▓▓
     ▒▒▒▒▒▒▒▒
          ░░░░░░░░
               ███████████
```

> **The further a moment is from now, the less information it retains.**

---

# Temporal Layers

Every previous frame can change according to its temporal age.

```text id="ghosf-temporal-profile"
PAST FRAME
    │
    ▼
TEMPORAL AGE
    │
    ▼
┌──────────────────┐
│ TEMPORAL PROFILE │
├──────────────────┤
│ opacity          │
│ resolution       │
│ blur             │
│ color            │
│ position         │
│ scale            │
│ transformation   │
└──────────────────┘
    │
    ▼
TEMPORAL LAYER
```

```text id="ghosf-layer-age"
DISTANT PAST
large pixels • low detail • low opacity

OLDER PAST
medium pixels • degraded detail

RECENT PAST
near-full resolution • mostly intact

NOW
full resolution • present reality
```

This allows effects to combine:

```text id="ghosf-combinations"
GHOST + PIXEL DECAY + COLOR AGE + TEMPORAL DRIFT
```

or:

```text id="ghosf-heavy-pixel"
GHOST + HEAVY PIXEL DECAY + NO OPACITY DECAY
```

---

# Ghosting

Previous moments can be layered onto the present.

```text id="ghosf-ghost-stack"
CURRENT
+
RECENT PAST
+
OLDER PAST
+
DISTANT PAST
```

Each layer can have independent temporal properties:

```text id="ghosf-time-properties"
TIME
 │
 ├── opacity
 ├── resolution
 ├── blur
 ├── color
 ├── position
 └── transformation
```

---

# Pixel Decay

Older frames are progressively downscaled, then enlarged using nearest-neighbor scaling.

```text id="ghosf-pixel-pipeline"
PREVIOUS FRAME
      ↓
TEMPORAL AGE
      ↓
CALCULATE PIXEL SIZE
      ↓
DOWNSCALE
      ↓
UPSCALE (NEAREST NEIGHBOR)
      ↓
APPLY OPACITY
      ↓
BLEND WITH PRESENT
```

Example:

```text id="ghosf-resolution-example"
1920 × 1080
    ↓
120 × 68
    ↓
1920 × 1080
```

**Blur** means the past becomes soft.

**Pixelation** means the past loses information.

GHOSF can eventually use both.

---

# Temporal Curves

Temporal decay can follow different patterns.

```text id="ghosf-linear"
LINEAR

1 → 2 → 4 → 6 → 8 → 10 → 12 → 16
```

```text id="ghosf-exponential"
EXPONENTIAL

1 → 1 → 1 → 2 → 2 → 4 → 8 → 16
```

```text id="ghosf-memory"
MEMORY DECAY

1 → 2 → 2 → 4 → 4 → 8 → 8 → 16
```

Recent moments can remain detailed while distant moments rapidly lose information.

---

# Temporal Camera Tricks

GHOSF is designed as a collection of temporal camera experiments.

## Ghost

Previous frames remain visible behind the present.

```text id="ghosf-ghost"
▓▓▓▓ → ▒▒▒▒ → ░░░░ → ████████
PAST                       NOW
```

## Temporal Reverb

Like audio echoes, but across time.

```text id="ghosf-reverb"
NOW
-1
-2
-4
-8
-16
```

```text id="ghosf-reverb-memory"
RECENT DETAIL
+
MEDIUM MEMORY
+
DISTANT MEMORY
```

## Motion Echo

Retain movement while keeping the background relatively stable.

```text id="ghosf-motion-echo"
      ◉
    ◉
  ◉
◉
```

## Time Slice

Different areas of the image represent different moments.

```text id="ghosf-time-slice"
| t-10 | t-8 | t-6 | t-4 | t-2 | NOW |
```

Directions may include:

```text id="ghosf-slice-directions"
VERTICAL • HORIZONTAL • DIAGONAL • RADIAL • RANDOM
```

## Temporal Scan / Slit Scan

Time moves through physical space.

```text id="ghosf-slit-scan"
TIME → → → → →

| frame 1 | frame 2 | frame 3 | frame 4 |
```

## RGB Time Split

Different color channels represent different moments.

```text id="ghosf-rgb-time"
RED   = NOW
GREEN = RECENT PAST
BLUE  = OLDER PAST
```

## Temporal Drift

Older moments shift through space.

```text id="ghosf-drift"
NOW
    ██████

t-1
  ██████

t-2
██████
```

## Time Tunnel

Previous moments scale inward or outward.

```text id="ghosf-tunnel"
NOW
████████████████

PAST
  ████████████

OLDER
    ████████

OLDER
      ████
```

## More experiments

- Temporal Mirror
- Color Age
- Temporal Edge Trails
- Ghost Silhouettes
- Motion-based ghosting
- Blur decay
- Scale decay
- Future + past layering

---

# The GHOSF Engine

```text id="ghosf-engine"
PREVIOUS FRAME
      │
      ▼
 TEMPORAL AGE
      │
 ┌────┼────┐
 ▼    ▼    ▼
OPACITY
RESOLUTION
TRANSFORMATION
 └────┼────┘
      ▼
TEMPORAL LAYER
      │
      ▼
 COMPOSITOR
      │
      ▼
CURRENT REALITY
```

GHOSF effects are not necessarily single filters.

They are rules describing what happens to an image as it moves further away from the present.

---

# Initial Goals

The first version will focus on:

- Drag-and-drop desktop GUI
- Python + FFmpeg
- Configurable frame interval
- Configurable ghost history
- Temporal opacity decay
- **Temporal pixel decay**
- Nearest-neighbor pixelation
- Blend modes
- Original audio preservation
- Progress reporting
- End fade
- Cubic Bézier-inspired temporal curves

The initial visual identity:

```text id="ghosf-identity"
SHARP PRESENT
+
PIXELATED PAST
+
TEMPORAL LAYERS
```

> **GHOSF turns the loss of information through time into an image.**