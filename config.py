import json
import os
import sys

# This works both when running as .py and as a PyInstaller .exe
if getattr(sys, 'frozen', False):
    # Running as compiled exe — use the folder where the exe sits
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as normal python script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")


def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)


settings = load_settings()