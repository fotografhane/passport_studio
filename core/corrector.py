import cv2
import numpy as np
from PIL import Image


MM_PER_INCH = 25.4


def mm_to_pixels(mm, dpi):
    return int((mm / MM_PER_INCH) * dpi)


def _warp_perspective(image_pil, pts):
    """Core perspective warp — returns just the flattened document, no canvas."""
    image = np.array(image_pil.convert("RGB"))
    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    pts = np.array(pts, dtype="float32")
    tl, tr, br, bl = pts

    width_top    = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    max_width    = int(max(width_top, width_bottom))

    height_left  = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)
    max_height   = int(max(height_left, height_right))

    max_width  = max(max_width, 10)
    max_height = max(max_height, 10)

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(image_bgr, M, (max_width, max_height))

    return Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))


def _place_on_a4(doc_img: Image.Image, settings: dict) -> Image.Image:
    """Center a document image on a white A4 canvas with padding."""
    dpi     = settings["dpi"]
    padding = mm_to_pixels(settings.get("padding_mm", 10), dpi)

    a4_w = mm_to_pixels(settings["a4_width_mm"],  dpi)
    a4_h = mm_to_pixels(settings["a4_height_mm"], dpi)

    doc_w, doc_h = doc_img.size
    available_w = a4_w - 2 * padding
    available_h = a4_h - 2 * padding

    scale = min(available_w / doc_w, available_h / doc_h)
    new_w = int(doc_w * scale)
    new_h = int(doc_h * scale)

    doc_img = doc_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    a4 = Image.new("RGB", (a4_w, a4_h), "white")
    x = (a4_w - new_w) // 2
    y = (a4_h - new_h) // 2
    a4.paste(doc_img, (x, y))

    return a4


# ── Public A4-canvas versions (used by Single Page Crop tab) ────────────────

def perspective_correct(image_pil, pts, settings):
    """Flatten a tilted document and center it on a white A4 sheet."""
    warped = _warp_perspective(image_pil, pts)
    return _place_on_a4(warped, settings)


def crop_only(image_pil, pts, settings):
    """Crop the bounding box of the document (no warp) and center on A4."""
    pts = np.array(pts, dtype="float32")
    x_coords = pts[:, 0]
    y_coords = pts[:, 1]
    x1, x2 = int(min(x_coords)), int(max(x_coords))
    y1, y2 = int(min(y_coords)), int(max(y_coords))

    cropped = image_pil.crop((x1, y1, x2, y2))
    return _place_on_a4(cropped, settings)


# ── Public RAW versions — no A4 canvas (used for ID card crop dialog) ───────

def perspective_correct_raw(image_pil, pts):
    """Flatten a tilted card/document and return just the warped image."""
    return _warp_perspective(image_pil, pts)


def crop_only_raw(image_pil, pts):
    """Crop the bounding box only (no warp, no canvas) — just the region."""
    pts = np.array(pts, dtype="float32")
    x_coords = pts[:, 0]
    y_coords = pts[:, 1]
    x1, x2 = int(min(x_coords)), int(max(x_coords))
    y1, y2 = int(min(y_coords)), int(max(y_coords))
    return image_pil.crop((x1, y1, x2, y2))
