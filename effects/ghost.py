from PIL import Image, ImageChops

from core.curves import pixel_size


def pixelate(image, size):
    if size <= 1:
        return image.convert("RGBA")

    width, height = image.size
    small = (max(1, width // size), max(1, height // size))

    return image.convert("RGBA").resize(
        small,
        Image.Resampling.BOX,
    ).resize(
        (width, height),
        Image.Resampling.NEAREST,
    )


def apply_alpha(image, alpha):
    result = image.convert("RGBA").copy()
    alpha = max(0.0, min(1.0, alpha))
    channel = result.getchannel("A").point(lambda value: int(value * alpha))
    result.putalpha(channel)
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
            ImageChops.multiply(
                ImageChops.invert(base_rgb),
                ImageChops.invert(layer_rgb),
            )
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
        size = pixel_size(
            age=age,
            history=settings.ghost_history,
            maximum=settings.max_pixel_size,
            curve=settings.pixel_curve,
        )

        opacity = max(
            0.0,
            1.0 - age / (settings.ghost_history + 1),
        ) * fade_strength

        layer = apply_alpha(pixelate(image, size), opacity)
        result = blend_layer(result, layer, settings.blend_mode)

    return result
