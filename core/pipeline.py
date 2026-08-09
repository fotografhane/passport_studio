from PIL import Image
import cv2
import numpy as np

from config import settings
from core.canvas_engine import create_sheet
from core.face_detector import FaceDetector
from core.crop_engine import crop_passport
from core.background import make_white_background
from core.enhancer import auto_enhance

detector = FaceDetector()


def pil_to_cv(image):
    return cv2.cvtColor(
        np.array(image),
        cv2.COLOR_RGB2BGR
    )


def generate_passport_sheet(
    image_path,
    copies=12,
    smart_crop=True,
    white_background=True,
    enhance=True
):

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

    sheet = create_sheet(
        photo=image,
        copies=copies,
        settings=settings
    )

    return sheet