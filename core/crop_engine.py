from PIL import Image


def crop_passport(image, face):
    """
    Passport-aware crop.

    face = (x, y, w, h)
    """

    x, y, w, h = face

    img_w, img_h = image.size

    # Face centre
    cx = x + (w / 2)

    # Passport rules
    head_ratio = 0.50       # Head occupies ~75% of photo height
    top_margin = 0.22       # Space above head
    bottom_margin = 0.03    # Space below chin

    # Estimate crop height from detected face
    crop_h = h / head_ratio

    # 35:45 aspect ratio
    crop_w = crop_h * (35 / 45)

    # Position crop
    left = cx - crop_w / 2
    top = y - (crop_h * top_margin)

    right = left + crop_w
    bottom = top + crop_h

    # Expand if crop is too tight
    padding = 20

    left -= padding
    top -= padding
    right += padding
    bottom += padding

    # Clamp to image boundaries
    if left < 0:
        right -= left
        left = 0

    if top < 0:
        bottom -= top
        top = 0

    if right > img_w:
        shift = right - img_w
        left -= shift
        right = img_w

    if bottom > img_h:
        shift = bottom - img_h
        top -= shift
        bottom = img_h

    left = max(0, int(left))
    top = max(0, int(top))
    right = min(img_w, int(right))
    bottom = min(img_h, int(bottom))

    return image.crop((left, top, right, bottom))