from PIL import Image, ImageOps
import math

MM_PER_INCH = 25.4

def mm_to_pixels(mm, dpi):
    return int((mm / MM_PER_INCH) * dpi)


def create_sheet(photo, copies, settings):
    """
    Single customer A4 sheet (used by Single Customer tab).
    """
    dpi = settings["dpi"]

    page_width  = mm_to_pixels(210, dpi)
    page_height = mm_to_pixels(297, dpi)

    photo_width  = mm_to_pixels(settings["photo_width"],  dpi)
    photo_height = mm_to_pixels(settings["photo_height"], dpi)

    margin         = mm_to_pixels(settings["margin"],         dpi)
    horizontal_gap = mm_to_pixels(settings["horizontal_gap"], dpi)
    vertical_gap   = mm_to_pixels(settings["vertical_gap"],   dpi)

    columns = settings["columns"]
    rows    = math.ceil(copies / columns)

    sheet = Image.new("RGB", (page_width, page_height), "white")

    photo = photo.resize((photo_width, photo_height), Image.Resampling.LANCZOS)
    photo = ImageOps.expand(photo, border=2, fill="black")

    total_width = columns * photo_width + (columns - 1) * horizontal_gap
    start_x = (page_width - total_width) // 2
    start_y = margin

    for i in range(copies):
        row = i // columns
        col = i % columns
        x = start_x + col * (photo_width + horizontal_gap)
        y = start_y + row * (photo_height + vertical_gap)
        sheet.paste(photo, (x, y))

    return sheet


def create_combined_sheet(customers_data, settings):
    """
    Multiple customers on one A4 sheet, placed top to bottom in order.

    customers_data = list of dicts:
        {
            "photo":  PIL.Image,  # already processed
            "copies": int,
            "label":  str,
        }
    """
    dpi = settings["dpi"]

    page_width  = mm_to_pixels(210, dpi)
    page_height = mm_to_pixels(297, dpi)

    photo_width  = mm_to_pixels(settings["photo_width"],  dpi)
    photo_height = mm_to_pixels(settings["photo_height"], dpi)

    margin         = mm_to_pixels(settings["margin"],         dpi)
    horizontal_gap = mm_to_pixels(settings["horizontal_gap"], dpi)
    vertical_gap   = mm_to_pixels(settings["vertical_gap"],   dpi)

    columns = settings["columns"]

    sheet = Image.new("RGB", (page_width, page_height), "white")

    total_width = columns * photo_width + (columns - 1) * horizontal_gap
    start_x = (page_width - total_width) // 2

    current_y = margin

    for customer in customers_data:
        photo  = customer["photo"]
        copies = customer["copies"]

        photo = photo.resize((photo_width, photo_height), Image.Resampling.LANCZOS)
        photo = ImageOps.expand(photo, border=2, fill="black")

        rows = math.ceil(copies / columns)

        for i in range(copies):
            row = i // columns
            col = i % columns
            x = start_x + col * (photo_width + horizontal_gap)
            y = current_y + row * (photo_height + vertical_gap)
            sheet.paste(photo, (x, y))

        current_y += rows * (photo_height + vertical_gap)

    return sheet