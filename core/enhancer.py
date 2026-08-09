from PIL import ImageEnhance, ImageFilter


def auto_enhance(image):
    """
    Applies mild enhancements suitable for passport photos.
    Keeps the result natural without oversaturation.
    """

    # Brightness
    image = ImageEnhance.Brightness(image).enhance(1.05)

    # Contrast
    image = ImageEnhance.Contrast(image).enhance(1.08)

    # Color (Saturation)
    image = ImageEnhance.Color(image).enhance(1.09)

    # Sharpness
    image = ImageEnhance.Sharpness(image).enhance(1.20)

    # Small detail enhancement
    image = image.filter(ImageFilter.DETAIL)

    return image