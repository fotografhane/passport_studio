from PIL import Image
from rembg import remove


def make_white_background(image):

    output = remove(image,
    alpha_matting=True,
    alpha_matting_foreground_threshold=240,
    alpha_matting_background_threshold=10,
    alpha_matting_erode_size=6)

    white = Image.new(
        "RGBA",
        output.size,
        (255, 255, 255, 255)
    )

    white.alpha_composite(output)

    return white.convert("RGB")