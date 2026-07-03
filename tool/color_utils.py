"""Image recoloring utilities using Pillow."""
from PIL import Image
import colorsys
import numpy as np


def hue_shift(image: Image.Image, hue_delta: float) -> Image.Image:
    """Shift hue by hue_delta degrees (0-360)."""
    img = image.convert("RGBA")
    data = np.array(img, dtype=np.float32) / 255.0

    r, g, b, a = data[..., 0], data[..., 1], data[..., 2], data[..., 3]

    # Vectorised RGB -> HSV
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    delta = max_c - min_c

    v = max_c
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(max_c == 0, 0, delta / max_c)

    h = np.zeros_like(r)
    mask_r = (max_c == r) & (delta != 0)
    mask_g = (max_c == g) & (delta != 0)
    mask_b = (max_c == b) & (delta != 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        h[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6
        h[mask_g] = (b[mask_g] - r[mask_g]) / delta[mask_g] + 2
        h[mask_b] = (r[mask_b] - g[mask_b]) / delta[mask_b] + 4
    h = h / 6.0  # normalise to [0, 1]

    # Shift hue
    h = (h + hue_delta / 360.0) % 1.0

    # HSV -> RGB (vectorised)
    i = (h * 6).astype(int)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)

    i_mod = i % 6
    out_r = np.select(
        [i_mod == 0, i_mod == 1, i_mod == 2, i_mod == 3, i_mod == 4, i_mod == 5],
        [v, q, p, p, t, v]
    )
    out_g = np.select(
        [i_mod == 0, i_mod == 1, i_mod == 2, i_mod == 3, i_mod == 4, i_mod == 5],
        [t, v, v, q, p, p]
    )
    out_b = np.select(
        [i_mod == 0, i_mod == 1, i_mod == 2, i_mod == 3, i_mod == 4, i_mod == 5],
        [p, p, t, v, v, q]
    )

    out = np.stack([out_r, out_g, out_b, a], axis=-1)
    out = (np.clip(out, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def adjust_saturation(image: Image.Image, factor: float) -> Image.Image:
    """Multiply saturation by factor (1.0 = no change, 0 = greyscale)."""
    from PIL import ImageEnhance
    img = image.convert("RGBA")
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = ImageEnhance.Color(rgb).enhance(factor)
    r2, g2, b2 = rgb.split()
    return Image.merge("RGBA", (r2, g2, b2, a))


def adjust_brightness(image: Image.Image, factor: float) -> Image.Image:
    """Multiply brightness by factor (1.0 = no change)."""
    from PIL import ImageEnhance
    img = image.convert("RGBA")
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = ImageEnhance.Brightness(rgb).enhance(factor)
    r2, g2, b2 = rgb.split()
    return Image.merge("RGBA", (r2, g2, b2, a))


def apply_color_adjustments(
    image: Image.Image,
    hue: float = 0.0,
    saturation: float = 1.0,
    brightness: float = 1.0,
) -> Image.Image:
    img = image.copy()
    if hue != 0:
        img = hue_shift(img, hue)
    if saturation != 1.0:
        img = adjust_saturation(img, saturation)
    if brightness != 1.0:
        img = adjust_brightness(img, brightness)
    return img
