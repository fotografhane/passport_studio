import os
import threading
import numpy as np
from tkinter import filedialog, messagebox
from PIL import Image
import customtkinter as ctk

from config import settings
from core.id_layout import detect_cards_auto, build_id_layout
from core.enhancer import auto_enhance
from core.corrector import perspective_correct, crop_only
from core.detector import detect_document, default_corners
from core.printer import print_image
from ui.corner_editor import CornerEditor
from ui.crop_dialog import CropDialog
import cv2

PREVIEW_MAX = (620, 520)


def pil_to_ctk(pil_img, max_size=PREVIEW_MAX):
    img = pil_img.copy()
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)


def pil_to_cv(pil_img):
    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)


class IDTab(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._front_img  = None
        self._back_img   = None
        self._result     = None

        self._crop_image_path = None
        self._crop_image_pil  = None
        self._crop_doc_pts    = None
        self._crop_result     = None

        self._build()

    def _build(self):
        self.inner_tabs = ctk.CTkTabview(self)
        self.inner_tabs.pack(fill="both", expand=True, padx=4, pady=4)

        id_frame   = self.inner_tabs.add("ID Card Front & Back")
        crop_frame = self.inner_tabs.add("Single Page Crop")

        self._build_id_tab(id_frame)
        self._build_crop_tab(crop_frame)

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 1 — ID Card Front & Back Layout
    # ════════════════════════════════════════════════════════════════════════

    def _build_id_tab(self, parent):
        # SCROLLABLE left panel — fixes cut-off buttons on smaller screens
        left = ctk.CTkScrollableFrame(parent, width=290)
        left.pack(side="left", fill="y", padx=(6, 4), pady=6)

        right = ctk.CTkFrame(parent)
        right.pack(side="right", fill="both", expand=True, padx=(4, 6), pady=6)

        self._build_id_left(left)
        self._build_id_right(right)

    def _build_id_left(self, parent):
        ctk.CTkLabel(parent, text="ID Card Layout",
                     font=("Segoe UI", 15, "bold")).pack(pady=(14, 2))
        ctk.CTkLabel(parent, text="Front & Back on one A4 sheet",
                     text_color="gray60", font=("Segoe UI", 11)).pack(pady=(0, 10))

        ctk.CTkLabel(parent, text="── Auto Detect ──",
                     font=("Segoe UI", 11, "bold"),
                     text_color="#4a9eda").pack(pady=(4, 2))
        ctk.CTkLabel(parent,
                     text="Load one image with both sides\n(e.g. scanned sheet)",
                     text_color="gray60", font=("Segoe UI", 10),
                     wraplength=240).pack()
        ctk.CTkButton(parent, text="🔍 Auto Detect Both Cards",
                      command=self._auto_detect,
                      width=230, height=34).pack(pady=6)

        ctk.CTkFrame(parent, height=1, fg_color="gray40").pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(parent, text="── Manual Select ──",
                     font=("Segoe UI", 11, "bold"),
                     text_color="#4a9eda").pack(pady=(0, 4))

        # Front card
        front_frame = ctk.CTkFrame(parent, corner_radius=8)
        front_frame.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(front_frame, text="Front Side",
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        self.front_label = ctk.CTkLabel(front_frame, text="Not selected",
                                        text_color="gray60", font=("Segoe UI", 10))
        self.front_label.pack(anchor="w", padx=10)
        self.front_thumb = ctk.CTkLabel(front_frame, text="",
                                        height=60, fg_color=("gray80", "gray25"),
                                        corner_radius=6)
        self.front_thumb.pack(fill="x", padx=10, pady=4)

        ctk.CTkButton(front_frame, text="📂 Select Front",
                      command=self._select_front,
                      width=200, height=28).pack(pady=(0, 4))

        front_rotate_row = ctk.CTkFrame(front_frame, fg_color="transparent")
        front_rotate_row.pack(pady=(0, 4))
        ctk.CTkButton(front_rotate_row, text="↺ Rotate Left", width=95, height=26,
                      font=("Segoe UI", 10),
                      command=lambda: self._rotate_front(-90)).pack(side="left", padx=2)
        ctk.CTkButton(front_rotate_row, text="↻ Rotate Right", width=95, height=26,
                      font=("Segoe UI", 10),
                      command=lambda: self._rotate_front(90)).pack(side="left", padx=2)

        ctk.CTkButton(front_frame, text="✂ Crop / Adjust Front", width=200, height=26,
                      font=("Segoe UI", 10),
                      fg_color="#7d3c98", hover_color="#5b2c6f",
                      command=lambda: self._open_crop("front")).pack(pady=(0, 8))

        # Back card
        back_frame = ctk.CTkFrame(parent, corner_radius=8)
        back_frame.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(back_frame, text="Back Side",
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        self.back_label = ctk.CTkLabel(back_frame, text="Not selected",
                                       text_color="gray60", font=("Segoe UI", 10))
        self.back_label.pack(anchor="w", padx=10)
        self.back_thumb = ctk.CTkLabel(back_frame, text="",
                                       height=60, fg_color=("gray80", "gray25"),
                                       corner_radius=6)
        self.back_thumb.pack(fill="x", padx=10, pady=4)

        ctk.CTkButton(back_frame, text="📂 Select Back",
                      command=self._select_back,
                      width=200, height=28).pack(pady=(0, 4))

        back_rotate_row = ctk.CTkFrame(back_frame, fg_color="transparent")
        back_rotate_row.pack(pady=(0, 4))
        ctk.CTkButton(back_rotate_row, text="↺ Rotate Left", width=95, height=26,
                      font=("Segoe UI", 10),
                      command=lambda: self._rotate_back(-90)).pack(side="left", padx=2)
        ctk.CTkButton(back_rotate_row, text="↻ Rotate Right", width=95, height=26,
                      font=("Segoe UI", 10),
                      command=lambda: self._rotate_back(90)).pack(side="left", padx=2)

        ctk.CTkButton(back_frame, text="✂ Crop / Adjust Back", width=200, height=26,
                      font=("Segoe UI", 10),
                      fg_color="#7d3c98", hover_color="#5b2c6f",
                      command=lambda: self._open_crop("back")).pack(pady=(0, 8))

        ctk.CTkFrame(parent, height=1, fg_color="gray40").pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(parent, text="Options",
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14)
        self.id_enhance_var    = ctk.BooleanVar(value=True)
        self.id_show_label_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(parent, text="Auto Enhance",
                        variable=self.id_enhance_var).pack(anchor="w", padx=20, pady=2)
        ctk.CTkCheckBox(parent, text="Show Front / Back Labels",
                        variable=self.id_show_label_var).pack(anchor="w", padx=20, pady=2)

        ctk.CTkLabel(parent, text="Gap between cards (mm):",
                     font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(6, 0))
        self.gap_var = ctk.StringVar(value="8")
        ctk.CTkEntry(parent, textvariable=self.gap_var, width=70).pack(anchor="w", padx=20)

        self.id_gen_btn = ctk.CTkButton(parent, text="⚙ Generate Layout",
                                        command=self._generate,
                                        state="disabled",
                                        width=230, height=36,
                                        font=("Segoe UI", 12))
        self.id_gen_btn.pack(pady=(14, 4))

        self.id_print_btn = ctk.CTkButton(parent, text="🖨 Print Sheet",
                                          command=self._print_id,
                                          state="disabled",
                                          fg_color="#1a6b3c", hover_color="#14532d",
                                          width=230, height=36,
                                          font=("Segoe UI", 12))
        self.id_print_btn.pack(pady=4)

        self.id_save_btn = ctk.CTkButton(parent, text="💾 Save Sheet",
                                         command=self._save_id,
                                         state="disabled",
                                         fg_color="#2471a3", hover_color="#1a5276",
                                         width=230, height=36,
                                         font=("Segoe UI", 12))
        self.id_save_btn.pack(pady=4)

        self.id_status = ctk.CTkLabel(parent, text="",
                                      text_color="gray60",
                                      font=("Segoe UI", 11), wraplength=240)
        self.id_status.pack(pady=(6, 20))

    def _build_id_right(self, parent):
        top_row = ctk.CTkFrame(parent, fg_color="transparent")
        top_row.pack(fill="x", padx=4, pady=(4, 2))

        front_pane = ctk.CTkFrame(top_row)
        front_pane.pack(side="left", fill="both", expand=True, padx=(4, 2))
        ctk.CTkLabel(front_pane, text="Front",
                     font=("Segoe UI", 11, "bold")).pack(pady=(6, 2))
        self.front_preview = ctk.CTkLabel(front_pane, text="No front image",
                                          fg_color=("gray82", "gray22"),
                                          corner_radius=8, height=180)
        self.front_preview.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        back_pane = ctk.CTkFrame(top_row)
        back_pane.pack(side="right", fill="both", expand=True, padx=(2, 4))
        ctk.CTkLabel(back_pane, text="Back",
                     font=("Segoe UI", 11, "bold")).pack(pady=(6, 2))
        self.back_preview = ctk.CTkLabel(back_pane, text="No back image",
                                         fg_color=("gray82", "gray22"),
                                         corner_radius=8, height=180)
        self.back_preview.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        result_pane = ctk.CTkFrame(parent)
        result_pane.pack(fill="both", expand=True, padx=4, pady=(2, 4))
        ctk.CTkLabel(result_pane, text="A4 Layout Preview",
                     font=("Segoe UI", 11, "bold")).pack(pady=(6, 2))
        self.id_result_preview = ctk.CTkLabel(result_pane,
                                              text="Generate to see layout",
                                              fg_color=("gray82", "gray22"),
                                              corner_radius=8)
        self.id_result_preview.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 2 — Single Page Crop (with draggable corner editor)
    # ════════════════════════════════════════════════════════════════════════

    def _build_crop_tab(self, parent):
        # SCROLLABLE left panel here too
        left = ctk.CTkScrollableFrame(parent, width=270)
        left.pack(side="left", fill="y", padx=(6, 4), pady=6)

        right = ctk.CTkFrame(parent)
        right.pack(side="right", fill="both", expand=True, padx=(4, 6), pady=6)

        self._build_crop_left(left)
        self._build_crop_right(right)

    def _build_crop_left(self, parent):
        ctk.CTkLabel(parent, text="Single Page Crop",
                     font=("Segoe UI", 15, "bold")).pack(pady=(14, 2))
        ctk.CTkLabel(parent,
                     text="Crop & straighten any document\ncertificate, receipt, slip, ID",
                     text_color="gray60", font=("Segoe UI", 11),
                     wraplength=230).pack(pady=(0, 12))

        ctk.CTkButton(parent, text="📂 Open Image",
                      command=self._crop_open,
                      width=220, height=36,
                      font=("Segoe UI", 12)).pack(pady=(0, 4))

        self.crop_file_label = ctk.CTkLabel(parent, text="No file selected",
                                            text_color="gray60",
                                            font=("Segoe UI", 10),
                                            wraplength=220)
        self.crop_file_label.pack(pady=(0, 8))

        # Rotate row for the crop source image
        rotate_row = ctk.CTkFrame(parent, fg_color="transparent")
        rotate_row.pack(pady=(0, 10))
        ctk.CTkButton(rotate_row, text="↺ Rotate Left", width=105, height=28,
                      font=("Segoe UI", 11),
                      command=lambda: self._rotate_crop(-90)).pack(side="left", padx=2)
        ctk.CTkButton(rotate_row, text="↻ Rotate Right", width=105, height=28,
                      font=("Segoe UI", 11),
                      command=lambda: self._rotate_crop(90)).pack(side="left", padx=2)

        ctk.CTkFrame(parent, height=1, fg_color="gray40").pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(parent, text="Output Mode",
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(4, 4))
        self.crop_mode_var = ctk.StringVar(value="correct")
        ctk.CTkRadioButton(parent,
                           text="Perspective Correct\n(flattens tilted docs)",
                           variable=self.crop_mode_var,
                           value="correct").pack(anchor="w", padx=20, pady=4)
        ctk.CTkRadioButton(parent,
                           text="Crop Only\n(keeps original angle)",
                           variable=self.crop_mode_var,
                           value="crop").pack(anchor="w", padx=20, pady=4)

        ctk.CTkFrame(parent, height=1, fg_color="gray40").pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(parent, text="Options",
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14)
        self.crop_enhance_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(parent, text="Auto Enhance",
                        variable=self.crop_enhance_var).pack(anchor="w", padx=20, pady=4)

        self.crop_detect_btn = ctk.CTkButton(parent, text="🔍 Detect Document",
                                             command=self._crop_detect,
                                             state="disabled",
                                             width=220, height=34,
                                             font=("Segoe UI", 12))
        self.crop_detect_btn.pack(pady=(10, 4))

        self.crop_process_btn = ctk.CTkButton(parent, text="⚙ Process & Crop",
                                              command=self._crop_process,
                                              state="disabled",
                                              width=220, height=34,
                                              font=("Segoe UI", 12))
        self.crop_process_btn.pack(pady=4)

        self.crop_print_btn = ctk.CTkButton(parent, text="🖨 Print",
                                            command=self._crop_print,
                                            state="disabled",
                                            fg_color="#1a6b3c", hover_color="#14532d",
                                            width=220, height=34,
                                            font=("Segoe UI", 12))
        self.crop_print_btn.pack(pady=4)

        self.crop_save_btn = ctk.CTkButton(parent, text="💾 Save",
                                           command=self._crop_save,
                                           state="disabled",
                                           fg_color="#2471a3", hover_color="#1a5276",
                                           width=220, height=34,
                                           font=("Segoe UI", 12))
        self.crop_save_btn.pack(pady=4)

        self.crop_status = ctk.CTkLabel(parent, text="",
                                        text_color="gray60",
                                        font=("Segoe UI", 11), wraplength=230)
        self.crop_status.pack(pady=(6, 20))

    def _build_crop_right(self, parent):
        ctk.CTkLabel(parent, text="Drag the red corner dots to match the document edges",
                     font=("Segoe UI", 11), text_color="gray60").pack(pady=(6, 2))

        editor_frame = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=8)
        editor_frame.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        self.corner_editor = CornerEditor(editor_frame, width=700, height=420)
        self.corner_editor.pack(fill="both", expand=True, padx=4, pady=4)

        result_pane = ctk.CTkFrame(parent)
        result_pane.pack(fill="both", expand=True, padx=6, pady=(2, 6))
        ctk.CTkLabel(result_pane, text="Result (A4)",
                     font=("Segoe UI", 11, "bold")).pack(pady=(6, 2))
        self.crop_result_preview = ctk.CTkLabel(result_pane,
                                                text="Result will appear here",
                                                fg_color=("gray82", "gray22"),
                                                corner_radius=8)
        self.crop_result_preview.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # ════════════════════════════════════════════════════════════════════════
    #  ID CARD HANDLERS
    # ════════════════════════════════════════════════════════════════════════

    def _auto_detect(self):
        path = filedialog.askopenfilename(
            title="Open image with both front & back",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if not path:
            return
        self._id_set_status("🔍 Detecting cards…")

        def _worker():
            img = Image.open(path).convert("RGB")
            cards = detect_cards_auto(img)
            self.after(0, lambda: self._on_auto_detected(cards))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_auto_detected(self, cards):
        if len(cards) == 0:
            messagebox.showerror("Not Found",
                                 "Could not detect any cards.\n"
                                 "Try Manual Select instead.")
            self._id_set_status("❌ No cards detected")
            return
        if len(cards) >= 2:
            self._set_front(cards[0])
            self._set_back(cards[1])
            self._id_set_status("✅ Both cards detected! Rotate if needed, then Generate.")
        else:
            self._set_front(cards[0])
            self._id_set_status("1 card found. Select Back manually.")

    def _select_front(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if not path:
            return
        self._set_front(Image.open(path).convert("RGB"), os.path.basename(path))

    def _select_back(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if not path:
            return
        self._set_back(Image.open(path).convert("RGB"), os.path.basename(path))

    def _set_front(self, img, name="auto-detected"):
        self._front_img = img
        self.front_label.configure(text=name)
        self._update_thumb(self.front_thumb, img)
        self._update_preview_label(self.front_preview, img)
        self._check_id_ready()

    def _set_back(self, img, name="auto-detected"):
        self._back_img = img
        self.back_label.configure(text=name)
        self._update_thumb(self.back_thumb, img)
        self._update_preview_label(self.back_preview, img)
        self._check_id_ready()

    def _rotate_front(self, degrees):
        if self._front_img is None:
            messagebox.showinfo("No Image", "Select a Front image first.")
            return
        # PIL rotate is counter-clockwise for positive angles;
        # expand=True keeps the whole image after rotation
        self._front_img = self._front_img.rotate(-degrees, expand=True)
        self._update_thumb(self.front_thumb, self._front_img)
        self._update_preview_label(self.front_preview, self._front_img)

    def _rotate_back(self, degrees):
        if self._back_img is None:
            messagebox.showinfo("No Image", "Select a Back image first.")
            return
        self._back_img = self._back_img.rotate(-degrees, expand=True)
        self._update_thumb(self.back_thumb, self._back_img)
        self._update_preview_label(self.back_preview, self._back_img)

    def _check_id_ready(self):
        if self._front_img and self._back_img:
            self.id_gen_btn.configure(state="normal")
            self._id_set_status("Both sides ready. Rotate if needed, then Generate.")

    def _open_crop(self, which):
        img = self._front_img if which == "front" else self._back_img
        if img is None:
            messagebox.showinfo("No Image",
                               f"Select the {which.capitalize()} image first.")
            return

        title = f"Crop / Adjust {which.capitalize()} Side"

        def _on_confirm(cropped_img):
            if which == "front":
                self._set_front(cropped_img, self.front_label.cget("text"))
            else:
                self._set_back(cropped_img, self.back_label.cget("text"))
            self._id_set_status(f"✅ {which.capitalize()} cropped. Ready to Generate.")

        CropDialog(self, img, settings, title=title, on_confirm=_on_confirm)

    def _generate(self):
        if not self._front_img or not self._back_img:
            return
        self.id_gen_btn.configure(state="disabled", text="⏳ Generating…")
        self.id_print_btn.configure(state="disabled")
        self.id_save_btn.configure(state="disabled")
        self._id_set_status("Building layout…")

        enhance     = self.id_enhance_var.get()
        show_labels = self.id_show_label_var.get()
        try:
            gap = float(self.gap_var.get())
        except ValueError:
            gap = 8.0

        front = self._front_img.copy()
        back  = self._back_img.copy()

        def _worker():
            front_e = auto_enhance(front) if enhance else front
            back_e  = auto_enhance(back)  if enhance else back
            result  = build_id_layout(
                front=front_e, back=back_e,
                settings=settings,
                label_front="▲ Front Side",
                label_back="▼ Back Side",
                show_labels=show_labels,
                card_gap_mm=gap,
            )
            self.after(0, lambda: self._on_id_generated(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_id_generated(self, result):
        self._result = result
        self.id_gen_btn.configure(state="normal", text="⚙ Generate Layout")
        self.id_print_btn.configure(state="normal")
        self.id_save_btn.configure(state="normal")
        ctk_img = pil_to_ctk(result, (600, 460))
        self.id_result_preview.configure(image=ctk_img, text="")
        self.id_result_preview.image = ctk_img
        self._id_set_status("✅ Layout ready!")

    def _print_id(self):
        if not self._result:
            return
        try:
            print_image(self._result)
            self._id_set_status("🖨 Sent to printer")
        except Exception as e:
            messagebox.showerror("Print Error", str(e))

    def _save_id(self):
        if not self._result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")],
            initialfile="id_card_layout.jpg")
        if not path:
            return
        try:
            self._result.save(path, quality=95)
            messagebox.showinfo("Saved", f"Saved to:\n{path}")
            self._id_set_status("💾 Saved!")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    # ════════════════════════════════════════════════════════════════════════
    #  SINGLE PAGE CROP HANDLERS
    # ════════════════════════════════════════════════════════════════════════

    def _crop_open(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if not path:
            return
        self._crop_image_path = path
        self._crop_image_pil  = Image.open(path).convert("RGB")
        self._crop_result     = None
        self.crop_file_label.configure(text=os.path.basename(path))

        self.crop_detect_btn.configure(state="normal")
        self.crop_print_btn.configure(state="disabled")
        self.crop_save_btn.configure(state="disabled")
        self._crop_set_status("Image loaded. Rotate if needed, then Detect Document.")

        self._crop_reload_editor()
        self.crop_process_btn.configure(state="normal")

    def _rotate_crop(self, degrees):
        if self._crop_image_pil is None:
            messagebox.showinfo("No Image", "Open an image first.")
            return
        self._crop_image_pil = self._crop_image_pil.rotate(-degrees, expand=True)
        self._crop_reload_editor()

    def _crop_reload_editor(self):
        """(Re)load the current crop image into the corner editor with a fresh default box."""
        w, h = self._crop_image_pil.size
        corners = default_corners(w, h)
        self._crop_doc_pts = corners
        self.after(50, lambda: self.corner_editor.load_image(self._crop_image_pil, corners))

    def _crop_detect(self):
        self.crop_detect_btn.configure(state="disabled", text="🔍 Detecting…")
        self._crop_set_status("Detecting edges…")

        def _worker():
            cv_img = pil_to_cv(self._crop_image_pil)
            pts = detect_document(cv_img)
            self.after(0, lambda: self._on_crop_detected(pts))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_crop_detected(self, pts):
        self.crop_detect_btn.configure(state="normal", text="🔍 Detect Document")

        if pts is None:
            w, h = self._crop_image_pil.size
            pts = default_corners(w, h)
            self._crop_set_status("⚠ Auto-detect unsure — adjust the corners manually below.")
        else:
            self._crop_set_status("✅ Detected! Drag corners to fine-tune, then Process.")

        self._crop_doc_pts = pts
        self.corner_editor.reset_corners(pts)
        self.crop_process_btn.configure(state="normal")

    def _crop_process(self):
        if self._crop_image_pil is None:
            return

        pts = np.array(self.corner_editor.get_corners_in_image_coords(), dtype="float32")

        self.crop_process_btn.configure(state="disabled", text="⚙ Processing…")
        self._crop_set_status("Processing…")

        mode    = self.crop_mode_var.get()
        enhance = self.crop_enhance_var.get()
        img     = self._crop_image_pil

        def _worker():
            if mode == "correct":
                result = perspective_correct(img, pts, settings)
            else:
                result = crop_only(img, pts, settings)
            if enhance:
                result = auto_enhance(result)
            self.after(0, lambda: self._on_crop_processed(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_crop_processed(self, result):
        self._crop_result = result
        self.crop_process_btn.configure(state="normal", text="⚙ Process & Crop")
        self.crop_print_btn.configure(state="normal")
        self.crop_save_btn.configure(state="normal")
        ctk_img = pil_to_ctk(result)
        self.crop_result_preview.configure(image=ctk_img, text="")
        self.crop_result_preview.image = ctk_img
        self._crop_set_status("✅ Done! Save or Print.")

    def _crop_print(self):
        if not self._crop_result:
            return
        try:
            print_image(self._crop_result)
            self._crop_set_status("🖨 Sent to printer")
        except Exception as e:
            messagebox.showerror("Print Error", str(e))

    def _crop_save(self):
        if not self._crop_result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")],
            initialfile="cropped_document.jpg")
        if not path:
            return
        try:
            self._crop_result.save(path, quality=95)
            messagebox.showinfo("Saved", f"Saved to:\n{path}")
            self._crop_set_status("💾 Saved!")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    # ════════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _update_thumb(self, label, img):
        t = img.copy()
        t.thumbnail((220, 65), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=t, dark_image=t, size=t.size)
        label.configure(image=ctk_img, text="")
        label.image = ctk_img

    def _update_preview_label(self, label, img):
        t = img.copy()
        t.thumbnail((300, 180), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=t, dark_image=t, size=t.size)
        label.configure(image=ctk_img, text="")
        label.image = ctk_img

    def _id_set_status(self, msg):
        self.id_status.configure(text=msg)

    def _crop_set_status(self, msg):
        self.crop_status.configure(text=msg)
