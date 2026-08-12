# PassportStudio.spec
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_all, copy_metadata

datas, binaries, hiddenimports = [], [], []

# ── collect full packages (data files + binaries + submodules)
for pkg in ['rembg', 'onnxruntime', 'pymatting', 'customtkinter', 'PIL']:
    tmp = collect_all(pkg)
    datas    += tmp[0]
    binaries += tmp[1]
    hiddenimports += tmp[2]

# ── copy package metadata (fixes "PackageNotFoundError: No package metadata")
for pkg in ['rembg', 'pymatting', 'onnxruntime', 'Pillow',
            'numpy', 'opencv-python', 'customtkinter', 'tqdm',
            'pooch', 'requests', 'click']:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# ── opencv haar cascade xmls
import cv2
cv2_dir = os.path.dirname(cv2.__file__)
datas += [(os.path.join(cv2_dir, 'data', '*.xml'), 'cv2/data')]

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'cv2',
        'numpy',
        'rembg',
        'pymatting',
        'pymatting.alpha.estimate_alpha_cf',
        'pymatting.alpha.estimate_alpha_knn',
        'pymatting.alpha.estimate_alpha_lbdm',
        'pymatting.foreground.estimate_foreground_ml',
        'pymatting.util.util',
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi._pybind_state',
        'win32api',
        'win32print',
        'importlib.metadata',
    ],
    hookspath=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ── onedir build: no re-extraction to temp folder on every launch,
#    so startup is fast after the first run.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PassportStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX compression slows down startup — skip it
    console=False,
    windowed=True,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PassportStudio',
)
