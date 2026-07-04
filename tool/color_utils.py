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


def _parse_hex(color_hex: str) -> tuple[float, float, float]:
    h = color_hex.lstrip('#')
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    return int(h[0:2], 16)/255.0, int(h[2:4], 16)/255.0, int(h[4:6], 16)/255.0


def _rgb_to_hls_vec(r: np.ndarray, g: np.ndarray, b: np.ndarray):
    """Vectorised RGB→HLS (all arrays 0-1). Returns h, l, s arrays."""
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    l = (cmax + cmin) / 2.0

    with np.errstate(divide='ignore', invalid='ignore'):
        s = np.where(delta == 0, 0.0,
                     delta / np.where(l < 0.5, (cmax + cmin),
                                      2.0 - cmax - cmin))

    h = np.zeros_like(r)
    mask_r = (cmax == r) & (delta != 0)
    mask_g = (cmax == g) & (delta != 0)
    mask_b = (cmax == b) & (delta != 0)
    with np.errstate(divide='ignore', invalid='ignore'):
        h[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6
        h[mask_g] = (b[mask_g] - r[mask_g]) / delta[mask_g] + 2
        h[mask_b] = (r[mask_b] - g[mask_b]) / delta[mask_b] + 4
    h = h / 6.0

    return h, l, s


def _hls_to_rgb_vec(h: np.ndarray, l: np.ndarray, s: np.ndarray):
    """Vectorised HLS→RGB. Returns r, g, b arrays 0-1."""
    c  = (1.0 - np.abs(2.0 * l - 1.0)) * s
    x  = c * (1.0 - np.abs((h * 6.0) % 2.0 - 1.0))
    m  = l - c / 2.0
    hi = (h * 6.0).astype(int) % 6

    r = np.select([hi==0, hi==1, hi==2, hi==3, hi==4, hi==5], [c, x, 0, 0, x, c])
    g = np.select([hi==0, hi==1, hi==2, hi==3, hi==4, hi==5], [x, c, c, x, 0, 0])
    b = np.select([hi==0, hi==1, hi==2, hi==3, hi==4, hi==5], [0, 0, x, c, c, x])

    return np.clip(r + m, 0, 1), np.clip(g + m, 0, 1), np.clip(b + m, 0, 1)


def apply_rim_tint(
    image: Image.Image,
    color_hex: str = '#ffffff',
    strength: float = 0.0,
    brightness_delta: float = 0.0,
) -> Image.Image:
    """Colorize a rim image: impose chosen hue+saturation while keeping original luminance.

    strength 0.0 = original greyscale, 1.0 = fully colorized.
    brightness_delta: -1.0 to +1.0 additive shift applied to lightness.
    """
    if strength <= 0.0 and brightness_delta == 0.0:
        return image.copy()

    img  = image.convert('RGBA')
    arr  = np.array(img, dtype=np.float32)
    rgb  = arr[..., :3] / 255.0
    alpha = arr[..., 3:4]

    # Parse target color → get its hue and saturation in HLS
    cr, cg, cb = _parse_hex(color_hex)
    _, _, target_s = _rgb_to_hls_vec(
        np.array([[[cr]]]), np.array([[[cg]]]), np.array([[[cb]]])
    )
    import colorsys
    target_h, _, _ = colorsys.rgb_to_hls(cr, cg, cb)
    target_s_val = float(target_s[0, 0, 0])

    # Convert image pixels to HLS
    h_img, l_img, _ = _rgb_to_hls_vec(rgb[..., 0], rgb[..., 1], rgb[..., 2])

    # Apply brightness delta to lightness
    l_out = np.clip(l_img + brightness_delta, 0.0, 1.0)

    if strength > 0.0:
        # Blend: at strength=1 use target_h/target_s, at 0 keep greyscale (s=0)
        h_out = np.full_like(h_img, target_h)
        s_out = np.full_like(h_img, target_s_val * strength)
        # Blend hue only where we're actually adding saturation
        h_final = h_img * (1.0 - strength) + h_out * strength
        r_out, g_out, b_out = _hls_to_rgb_vec(h_final, l_out, s_out)
    else:
        # brightness only — keep greyscale
        r_out = g_out = b_out = l_out

    out = np.stack([r_out, g_out, b_out], axis=-1)
    out = np.concatenate([np.clip(out * 255, 0, 255), alpha], axis=-1).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')
