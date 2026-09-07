import math


def pixel_size(age, history, maximum, curve):
    if history <= 0 or maximum <= 1:
        return 1

    t = max(0.0, min(1.0, age / history))

    if curve == "exponential":
        t = t * t
    elif curve == "memory":
        raw = 1 + (maximum - 1) * t
        power = max(0, round(math.log(max(raw, 1), 2)))
        return min(maximum, max(1, 2 ** power))

    return max(1, round(1 + (maximum - 1) * t))


def cubic_bezier_y(t, p1x, p1y, p2x, p2y):
    lo, hi = 0.0, 1.0

    for _ in range(28):
        u = (lo + hi) / 2
        x = (
            3 * (1 - u) ** 2 * u * p1x
            + 3 * (1 - u) * u ** 2 * p2x
            + u ** 3
        )
        if x < t:
            lo = u
        else:
            hi = u

    u = (lo + hi) / 2
    return (
        3 * (1 - u) ** 2 * u * p1y
        + 3 * (1 - u) * u ** 2 * p2y
        + u ** 3
    )


def end_fade_strength(index, total, fade_frames, bezier):
    if not total or fade_frames <= 0:
        return 1.0

    start = max(0, total - fade_frames)
    if index < start:
        return 1.0

    if fade_frames <= 1:
        return 0.0

    t = (index - start) / (fade_frames - 1)
    t = max(0.0, min(1.0, t))
    eased = cubic_bezier_y(t, *bezier)
    return max(0.0, min(1.0, 1.0 - eased))
