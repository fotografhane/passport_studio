import os
import tempfile

import win32api
import win32print


def get_default_printer():
    return win32print.GetDefaultPrinter()


def print_image(image):

    temp = os.path.join(
        tempfile.gettempdir(),
        "passport_print.jpg"
    )

    image.save(temp, quality=100)

    printer = get_default_printer()

    win32api.ShellExecute(
        0,
        "print",
        temp,
        f'"{printer}"',
        ".",
        0
    )