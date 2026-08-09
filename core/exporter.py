import os
from PIL import Image
from config import settings


def save_output(image: Image.Image, original_path: str, suffix: str = "scanned") -> str:
    """
    Save output image to the output folder.
    Returns the saved file path.
    """
    output_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", settings["output_folder"]
    )
    os.makedirs(output_folder, exist_ok=True)

    base = os.path.splitext(os.path.basename(original_path))[0]
    out_path = os.path.join(output_folder, f"{base}_{suffix}.jpg")

    image.save(out_path, "JPEG", quality=95)
    return out_path