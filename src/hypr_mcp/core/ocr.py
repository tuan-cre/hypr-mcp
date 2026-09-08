"""Tesseract OCR. Preprocess (upscale/invert/sharpen), boxes in native coords."""

import io

from PIL import Image as PILImage, ImageOps, ImageFilter

from ..config import Settings
from ..errors import HyprMCPError, require_tool


def _pytesseract():
    try:
        import pytesseract
    except ImportError:
        raise HyprMCPError(
            "OCR needs the 'ocr' extra plus the tesseract binary: "
            "pipx inject hypr-mcp hypr-mcp[ocr] && pacman -S tesseract tesseract-data-eng"
        )
    return pytesseract


def preprocess(img: PILImage.Image, settings: Settings) -> PILImage.Image:
    w, h = img.size
    k = max(1, settings.ocr_upscale)
    if k != 1:
        img = img.resize((w * k, h * k), PILImage.LANCZOS)
    gray = img.convert("L")
    pixels = list(gray.getdata())
    if pixels and sum(pixels) / len(pixels) < 128:
        gray = ImageOps.invert(gray)
    return gray.filter(ImageFilter.SHARPEN)


def extract_text(image_bytes: bytes, settings: Settings) -> str:
    require_tool("tesseract")
    img = PILImage.open(io.BytesIO(image_bytes))
    return _pytesseract().image_to_string(preprocess(img, settings)).strip()


def extract_boxes(image_bytes: bytes, settings: Settings) -> list[dict]:
    """Word boxes in original-image coords (upscale compensated)."""
    require_tool("tesseract")
    img = PILImage.open(io.BytesIO(image_bytes))
    k = max(1, settings.ocr_upscale)
    pt = _pytesseract()
    data = pt.image_to_data(
        preprocess(img, settings), output_type=pt.Output.DICT
    )
    boxes = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        try:
            conf = int(float(data["conf"][i]))
        except ValueError:
            conf = -1
        if not text or conf < settings.ocr_min_conf:
            continue
        boxes.append({
            "text": text,
            "x": int(data["left"][i] // k),
            "y": int(data["top"][i] // k),
            "w": max(1, int(data["width"][i] // k)),
            "h": max(1, int(data["height"][i] // k)),
            "conf": conf,
        })
    return boxes


def find_text(boxes: list[dict], target: str) -> list[dict]:
    """Case-insensitive single-word substring, or exact multi-word phrase merge."""
    words = target.lower().split()
    if len(words) == 1:
        out = [b for b in boxes if words[0] in b["text"].lower()]
        out.sort(key=lambda b: b["conf"], reverse=True)
        return out
    matches = []
    for i in range(len(boxes) - len(words) + 1):
        span = boxes[i:i + len(words)]
        if [b["text"].lower() for b in span] != words:
            continue
        ys = [b["y"] for b in span]
        if max(ys) - min(ys) >= span[0]["h"] * 1.5:
            continue
        pad = 4
        x = max(0, span[0]["x"] - pad)
        y = max(0, min(b["y"] for b in span) - pad)
        right = max(b["x"] + b["w"] for b in span) + pad
        bottom = max(b["y"] + b["h"] for b in span) + pad
        matches.append({
            "text": " ".join(b["text"] for b in span),
            "x": x, "y": y, "w": right - x, "h": bottom - y,
            "conf": sum(b["conf"] for b in span) // len(span),
        })
    matches.sort(key=lambda b: b["conf"], reverse=True)
    return matches
