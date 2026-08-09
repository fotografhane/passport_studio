import threading
import numpy as np
import customtkinter as ctk
from PIL import Image
import cv2

from core.detector import detect_document, default_corners
from core.corrector import perspective_correct_raw, crop_only_raw
from ui.corner_editor import CornerEditor


def _pil_to_cv(pil_img):
    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)


class CropDialog(ctk.CTkToplevel):
    """
    Modal dialog: shows the image with draggable corner handles,
    lets the user auto-detect or manually adjust the crop box,
    then confirms to produce a cropped card image.

    Usage:
        CropDialog(parent, pil_image, settings, title="Crop Front Side",
                  on_confirm=lambda cropped_img: ...)
    """

    def __init__(self, master, pil_image: Image.Image, settings: dict,
                title="Crop / Adjust", on_confirm=None):
        super().__init__(master)
        self.title(title)
        self.geometry("820x650")
        self.transient(master)
        self.grab_set()

        self.settings = settings
        self.source_image = pil_image
        self.on_confirm = on_confirm
        self.mode_var = ctk.StringVar(value="crop")

        self._build()

        w, h = self.source_image.size
        corners = default_corners(w, h, margin_pct=0.04)
        self.after(80, lambda: self.editor.load_image(self.source_image, corners))

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))

        ctk.CTkLabel(top, text="Drag the red corner dots to match the card edges",
                     font=("Segoe UI", 12)).pack(side="left")

        ctk.CTkButton(top, text="🔍 Auto Detect", width=130,
                      command=self._auto_detect).pack(side="right", padx=4)

        editor_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=8)
        editor_frame.pack(fill="both", expand=True, padx=10, pady=4)

        self.editor = CornerEditor(editor_frame, width=780, height=460)
        self.editor.pack(fill="both", expand=True, padx=4, pady=4)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(4, 10))

        ctk.CTkRadioButton(bottom, text="Crop Only (keep angle)",
                           variable=self.mode_var, value="crop").pack(side="left", padx=6)
        ctk.CTkRadioButton(bottom, text="Straighten (perspective correct)",
                           variable=self.mode_var, value="correct").pack(side="left", padx=6)

        self.status_label = ctk.CTkLabel(bottom, text="", text_color="gray60")
        self.status_label.pack(side="left", padx=12)

        ctk.CTkButton(bottom, text="Cancel", width=100,
                      fg_color="#7f8c8d", hover_color="#626567",
                      command=self._cancel).pack(side="right", padx=4)
        self.confirm_btn = ctk.CTkButton(bottom, text="✅ Confirm Crop", width=150,
                                         fg_color="#1a6b3c", hover_color="#14532d",
                                         command=self._confirm)
        self.confirm_btn.pack(side="right", padx=4)

    def _auto_detect(self):
        self.status_label.configure(text="Detecting…")

        def _worker():
            cv_img = _pil_to_cv(self.source_image)
            pts = detect_document(cv_img)
            self.after(0, lambda: self._on_detected(pts))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_detected(self, pts):
        if pts is None:
            w, h = self.source_image.size
            pts = default_corners(w, h, margin_pct=0.04)
            self.status_label.configure(text="⚠ Not confident — adjust manually")
        else:
            self.status_label.configure(text="✅ Detected — fine-tune if needed")
        self.editor.reset_corners(pts)

    def _confirm(self):
        pts = np.array(self.editor.get_corners_in_image_coords(), dtype="float32")
        mode = self.mode_var.get()

        self.confirm_btn.configure(state="disabled", text="⏳ Processing…")
        self.status_label.configure(text="Processing…")

        def _worker():
            if mode == "correct":
                result = perspective_correct_raw(self.source_image, pts)
            else:
                result = crop_only_raw(self.source_image, pts)
            self.after(0, lambda: self._finish(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _finish(self, result):
        if self.on_confirm:
            self.on_confirm(result)
        self.destroy()

    def _cancel(self):
        self.destroy()
