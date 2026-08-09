from PIL import Image
from config import settings
from core.canvas_engine import create_combined_sheet
from core.face_detector import FaceDetector
from core.crop_engine import crop_passport
from core.background import make_white_background
from core.enhancer import auto_enhance
from core.pipeline import pil_to_cv

detector = FaceDetector()


def _process_photo(image_path, smart_crop, white_background, enhance):
    """Process a single photo through the full passport pipeline."""
    image = Image.open(image_path).convert("RGB")

    if smart_crop:
        cv_image = pil_to_cv(image)
        face = detector.detect(cv_image)
        if face is not None:
            image = crop_passport(image, face)

    if white_background:
        image = make_white_background(image)

    if enhance:
        image = auto_enhance(image)

    return image


def generate_batch(customers: list[dict]) -> dict:
    """
    Process all customers and combine onto one A4 sheet.

    Returns:
        {
            "combined_sheet": PIL.Image or None,
            "errors": list of {"label": str, "error": str}
        }
    """
    customers_data = []
    errors = []

    for idx, c in enumerate(customers):
        label = c.get("label") or f"Customer {idx + 1}"
        try:
            photo = _process_photo(
                image_path=c["image_path"],
                smart_crop=c.get("smart_crop", True),
                white_background=c.get("white_background", False),
                enhance=c.get("enhance", True),
            )
            customers_data.append({
                "photo":  photo,
                "copies": c.get("copies", 12),
                "label":  label,
            })
        except Exception as exc:
            errors.append({"label": label, "error": str(exc)})

    combined_sheet = None
    if customers_data:
        combined_sheet = create_combined_sheet(customers_data, settings)

    return {
        "combined_sheet": combined_sheet,
        "errors": errors,
    }