from PIL import Image, ImageChops, ImageEnhance


def apply_alpha(image, alpha):
    result = image.convert("RGBA").copy()
    alpha = max(0.0, min(1.0, alpha))
    channel = result.getchannel("A").point(lambda value: int(value * alpha))
    result.putalpha(channel)
    return result


def appearance(image, age, history, settings):
    """Apply progressively stronger appearance treatment to older moments."""
    t = max(0.0, min(1.0, age / max(1, history)))
    rgb = image.convert("RGB")

    # Controls are percentages. Their influence increases with temporal age.
    contrast = 1.0 + (settings.ghost_contrast / 100.0) * t
    brightness = 1.0 + (settings.ghost_brightness / 100.0) * t
    rgb = ImageEnhance.Contrast(rgb).enhance(max(0.0, contrast))
    rgb = ImageEnhance.Brightness(rgb).enhance(max(0.0, brightness))

    if settings.shadow_depth or settings.highlight_intensity:
        shadow = (settings.shadow_depth / 100.0) * t
        highlight = (settings.highlight_intensity / 100.0) * t
        lut = []
        for value in range(256):
            x = value / 255.0
            if x < 0.5:
                y = x * (1.0 - shadow * (1.0 - x * 2.0))
            else:
                y = x + (1.0 - x) * highlight * ((x - 0.5) * 2.0)
            lut.append(round(max(0.0, min(1.0, y)) * 255))
        rgb = rgb.point(lut * 3)

    result = rgb.convert("RGBA")
    result.putalpha(image.convert("RGBA").getchannel("A"))
    return result


def blend_layer(base, layer, mode):
    base = base.convert("RGBA")
    layer = layer.convert("RGBA")

    if mode == "normal":
        return Image.alpha_composite(base, layer)

    base_rgb = base.convert("RGB")
    layer_rgb = layer.convert("RGB")

    if mode == "screen":
        blended = ImageChops.invert(
            ImageChops.multiply(ImageChops.invert(base_rgb), ImageChops.invert(layer_rgb))
        ).convert("RGBA")
    elif mode == "additive":
        blended = ImageChops.add(base_rgb, layer_rgb, scale=1.0, offset=0).convert("RGBA")
    else:
        return Image.alpha_composite(base, layer)

    blended.putalpha(layer.getchannel("A"))
    return Image.alpha_composite(base, blended)


def compose(current, history_layers, settings, fade_strength=1.0):
    result = current.convert("RGBA")
    # Oldest first so recent moments sit closest to the present.
    for age, image in reversed(list(enumerate(history_layers, start=1))):
        opacity = max(0.0, 1.0 - age / (settings.ghost_history + 1)) * fade_strength
        layer = appearance(image, age, settings.ghost_history, settings)
        layer = apply_alpha(layer, opacity)
        result = blend_layer(result, layer, settings.blend_mode)
    return result
