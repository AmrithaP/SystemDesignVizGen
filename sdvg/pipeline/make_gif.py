# sdvg/pipeline/make_gif.py
from __future__ import annotations

from typing import List, Tuple
from PIL import Image, ImageEnhance


def _zoom_frame(img: Image.Image, scale: float) -> Image.Image:
    """Zoom from center, keep same canvas size."""
    w, h = img.size
    nw, nh = int(w * scale), int(h * scale)

    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)

    # center-crop back to original size
    left = (nw - w) // 2
    top = (nh - h) // 2
    return resized.crop((left, top, left + w, top + h))


def png_to_gif_pulse(
    png_path: str,
    gif_path: str,
    duration_ms: int = 120,
    loop: int = 0,
    scales: List[float] | None = None,
    add_fade_in: bool = False,
) -> str:
    """
    Creates a subtle pulse GIF from a single PNG.
    - scales controls zoom levels (e.g. [1.0, 1.02, 1.0])
    - add_fade_in adds a few frames that fade from dim->normal
    """
    if scales is None:
        scales = [1.00, 1.02, 1.03, 1.02, 1.00]

    base = Image.open(png_path).convert("RGBA")

    frames: List[Image.Image] = []

    if add_fade_in:
        # 4 fade-in frames
        for f in [0.4, 0.6, 0.8, 1.0]:
            enhancer = ImageEnhance.Brightness(base)
            frames.append(enhancer.enhance(f))

    for s in scales:
        frames.append(_zoom_frame(base, s))

    # Convert to palette for smaller GIF
    frames_p = [fr.convert("P", palette=Image.Palette.ADAPTIVE, colors=256) for fr in frames]

    frames_p[0].save(
        gif_path,
        save_all=True,
        append_images=frames_p[1:],
        duration=duration_ms,
        loop=loop,
        optimize=True,
        disposal=2,
    )
    return gif_path
