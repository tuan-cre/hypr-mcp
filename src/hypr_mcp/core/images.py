"""Image resize/compress. No subprocess, no hyprctl — pure Pillow."""

import io

from PIL import Image as PILImage
from mcp.server.mcpserver import Image


def resize_and_compress(
    png_bytes: bytes,
    max_width: int = 1440,
    quality: int = 75,
) -> tuple[Image, float]:
    """Resize to max_width and JPEG-compress. Returns (Image, scale)."""
    img = PILImage.open(io.BytesIO(png_bytes))
    scale = 1.0
    if img.width > max_width:
        scale = max_width / img.width
        img = img.resize((max_width, int(img.height * scale)), PILImage.LANCZOS)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return Image(data=buf.getvalue(), format="jpeg"), scale


def native_size(png_bytes: bytes) -> tuple[int, int]:
    img = PILImage.open(io.BytesIO(png_bytes))
    return img.width, img.height


def coord_help(img_w: int, img_h: int, native_w: int, native_h: int,
               origin_x: int, origin_y: int, scale: float) -> str:
    inv = 1.0 / scale if scale != 1.0 else 1.0
    return (
        f"Coordinate mapping: This {img_w}x{img_h} image covers screen region "
        f"starting at absolute ({origin_x}, {origin_y}), "
        f"native size {native_w}x{native_h}.\n"
        f"To convert image coordinates to absolute screen coordinates:\n"
        f"  screen_x = image_x * {inv:.2f} + {origin_x}\n"
        f"  screen_y = image_y * {inv:.2f} + {origin_y}\n"
        f"IMPORTANT: Always use absolute screen coordinates with mouse tools, "
        f"never raw image pixel positions."
    )
