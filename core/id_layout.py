import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

MM_PER_INCH = 25.4


def mm_to_pixels(mm, dpi):
    return int((mm / MM_PER_INCH) * dpi)


def detect_cards_auto(image_pil):
    """
    Detect all card regions in a scanned/photographed image
    that contains multiple cards on a white/light background.
    Returns list of PIL Images cropped per card, sorted top-to-bottom.
    """
    img = cv2.cvtColor(np.array(image_pil.convert("RGB")), cv2.COLOR_RGB2BGR)
    orig_h, orig_w = img.shape[:2]

    scale = 1200 / max(orig_h, orig_w)
    resized = cv2.resize(img, (int(orig_w * scale), int(orig_h * scale)))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    cards = []
    total_area = resized.shape[0] * resized.shape[1]

    for c in contours:
        pct = 100 * cv2.contourArea(c) / total_area
        if 3 < pct < 60:
            x, y, w, h = cv2.boundingRect(c)
            x0 = max(0, int(x / scale) - 8)
            y0 = max(0, int(y / scale) - 8)
            x1 = min(orig_w, int((x + w) / scale) + 8)
            y1 = min(orig_h, int((y + h) / scale) + 8)
            crop = image_pil.crop((x0, y0, x1, y1))
            cards.append((y0, crop))   # (y_position, image) for sorting

        if len(cards) == 2:
            break

    # Sort top-to-bottom so front comes first
    cards.sort(key=lambda t: t[0])
    return [c[1] for c in cards]


def build_id_layout(front: Image.Image,
                    back: Image.Image,
                    settings: dict,
                    label_front: str = "Front",
                    label_back: str = "Back",
                    show_labels: bool = True,
                    card_gap_mm: float = 8.0) -> Image.Image:
    """
    Place front and back ID card images on a white A4 sheet.
    Cards are centered horizontally, stacked vertically with a gap.
    """
    dpi     = settings["dpi"]
    padding = mm_to_pixels(settings.get("padding_mm", 10), dpi)
    gap     = mm_to_pixels(card_gap_mm, dpi)

    a4_w = mm_to_pixels(settings["a4_width_mm"],  dpi)
    a4_h = mm_to_pixels(settings["a4_height_mm"], dpi)

    sheet = Image.new("RGB", (a4_w, a4_h), "white")

    # Available space
    avail_w = a4_w - 2 * padding
    label_h = mm_to_pixels(6, dpi) if show_labels else 0

    # Each card gets roughly half the vertical space minus gap and labels
    slot_h = (a4_h - 2 * padding - gap - 2 * label_h) // 2

    def fit_card(card: Image.Image, max_w: int, max_h: int) -> Image.Image:
        scale = min(max_w / card.width, max_h / card.height)
        new_w = int(card.width  * scale)
        new_h = int(card.height * scale)
        return card.resize((new_w, new_h), Image.Resampling.LANCZOS)

    front_fit = fit_card(front, avail_w, slot_h)
    back_fit  = fit_card(back,  avail_w, slot_h)

    # Try to load a font for labels
    try:
        font = ImageFont.truetype("arial.ttf", mm_to_pixels(4, dpi))
    except Exception:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(sheet)

    def paste_card(card_img, y_start, label):
        cx = (a4_w - card_img.width) // 2
        if show_labels:
            # Draw label
            draw.text((padding, y_start), label,
                      fill=(100, 100, 100), font=font)
            y_start += label_h
        sheet.paste(card_img, (cx, y_start))
        return y_start + card_img.height

    y = padding
    y = paste_card(front_fit, y, label_front)
    y += gap
    paste_card(back_fit, y, label_back)

    return sheet