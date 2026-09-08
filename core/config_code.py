import base64
import hashlib
import json
import zlib


def encode_settings(settings):
    data = {
        "v": 1,
        "i": settings.ghost_frame_interval,
        "h": settings.ghost_history,
        "b": settings.blend_mode,
        "fe": settings.end_fade_enabled,
        "ff": settings.end_fade_frames,
        "bz": list(settings.fade_bezier),
        "c": settings.ghost_contrast,
        "s": settings.shadow_depth,
        "l": settings.highlight_intensity,
        "br": settings.ghost_brightness,
        "o": settings.optimize_output,
        "f": settings.output_format,
    }
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode().rstrip("=")


def short_fingerprint(settings, length=8):
    """Return a compact deterministic fingerprint for user-facing identifiers."""
    data = {
        "v": 1,
        "i": settings.ghost_frame_interval,
        "h": settings.ghost_history,
        "b": settings.blend_mode,
        "fe": settings.end_fade_enabled,
        "ff": settings.end_fade_frames,
        "bz": list(settings.fade_bezier),
        "c": settings.ghost_contrast,
        "s": settings.shadow_depth,
        "l": settings.highlight_intensity,
        "br": settings.ghost_brightness,
        "o": settings.optimize_output,
        "f": settings.output_format,
    }
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()[:length]


def decode_settings(code):
    code = code.strip()
    padding = "=" * (-len(code) % 4)
    try:
        raw = zlib.decompress(base64.urlsafe_b64decode(code + padding))
        data = json.loads(raw.decode())
    except Exception as exc:
        raise ValueError("Invalid ghosf configuration code.") from exc
    if data.get("v") != 1:
        raise ValueError("Unsupported ghosf configuration version.")
    return data
