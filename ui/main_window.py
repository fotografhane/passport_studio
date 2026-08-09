import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
from core.pipeline import generate_passport_sheet
import tempfile
import os
from core.printer import print_image
from ui.batch_tab import BatchTab
from ui.id_tab import IDTab


class PassportStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Passport Studio")
        self.geometry("1280x760")

        # ── single-customer state
        self.selected_image = None      # original file path (unrotated)
        self.working_image  = None      # PIL image, may be rotated
        self.generated_sheet = None
        self.output_file = None
        self.photo_count = ctk.StringVar(value="12")
        self.photo_size = ctk.StringVar(value="35 × 45 mm")

        self.face_detection   = ctk.BooleanVar(value=True)
        self.white_background = ctk.BooleanVar(value=False)
        self.auto_enhance     = ctk.BooleanVar(value=True)

        self.build_ui()

    # ── UI skeleton ──────────────────────────────────────────────────────────

    def build_ui(self):
        # ── Header: title + credit + About button
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 0))

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.pack(side="left")

        ctk.CTkLabel(title_block, text="Passport Studio",
                     font=("Segoe UI", 35, "bold")).pack(anchor="w")
        ctk.CTkLabel(title_block, text="by Sandeep Chahal   ·   @noob-214",
                     font=("Segoe UI", 19),
                     text_color="gray80").pack(anchor="w", pady=(2, 4))

        ctk.CTkButton(header, text="ℹ About", width=90, height=30,
                      fg_color="#3a3a3a", hover_color="#4a4a4a",
                      command=self._show_about).pack(side="right", pady=6)

        # Tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        # ── Tab 1: Single customer (original flow)
        single_tab = self.tabview.add("Single Customer")
        self._build_single_tab(single_tab)

        # ── Tab 2: Batch / multi-customer
        batch_tab_frame = self.tabview.add("Batch (Multiple Customers)")
        BatchTab(batch_tab_frame).pack(fill="both", expand=True)

        # ── Tab 3: ID Card Layout / Single Page Crop
        id_tab_frame = self.tabview.add("ID Card Layout")
        IDTab(id_tab_frame).pack(fill="both", expand=True)

    # ── About dialog ─────────────────────────────────────────────────────────

    def _show_about(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("About")
        dialog.geometry("340x220")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        ctk.CTkLabel(dialog, text="Passport Studio v1",
                     font=("Segoe UI", 20, "bold")).pack(pady=(28, 8))
        ctk.CTkLabel(dialog, text="Created by Sandeep Chahal",
                     font=("Segoe UI", 17)).pack(pady=(0, 2))
        ctk.CTkLabel(dialog, text="@noob-214",
                     font=("Segoe UI", 13),
                     text_color="gray60").pack(pady=(0, 16))

        ctk.CTkButton(dialog, text="Close", width=120,
                      command=dialog.destroy).pack(pady=(4, 10))

    # ── single-customer tab ───────────────────────────────────────────────────

    def _build_single_tab(self, parent):
        main = ctk.CTkFrame(parent)
        main.pack(fill="both", expand=True, padx=6, pady=6)

        left = ctk.CTkFrame(main, width=300)
        left.pack(side="left", fill="y", padx=10, pady=10)

        right = ctk.CTkFrame(main)
        right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkButton(left, text="Open Photo",
                      command=self.open_photo, width=220).pack(pady=10)

        # ── Rotate buttons — NEW
        rotate_row = ctk.CTkFrame(left, fg_color="transparent")
        rotate_row.pack(pady=(0, 10))
        ctk.CTkButton(rotate_row, text="↺ Rotate Left", width=105, height=28,
                      font=("Segoe UI", 11),
                      command=lambda: self.rotate_photo(-90)).pack(side="left", padx=2)
        ctk.CTkButton(rotate_row, text="↻ Rotate Right", width=105, height=28,
                      font=("Segoe UI", 11),
                      command=lambda: self.rotate_photo(90)).pack(side="left", padx=2)

        ctk.CTkLabel(left, text="Photo Size").pack()
        ctk.CTkComboBox(left,
                        values=["35 × 45 mm", "2 × 2 inch", "50 × 50 mm"],
                        variable=self.photo_size,
                        state="readonly", width=220).pack(pady=5)

        ctk.CTkLabel(left, text="Number of Photos").pack(pady=(15, 0))
        ctk.CTkComboBox(left,
                        values=["6", "12", "18", "24"],
                        variable=self.photo_count,
                        state="readonly", width=220).pack(pady=5)

        ctk.CTkLabel(left, text="Processing Options",
                     font=("Segoe UI", 14, "bold")).pack(pady=(20, 8))

        ctk.CTkCheckBox(left, text="Smart Crop",
                        variable=self.face_detection).pack(anchor="w",
                                                           padx=20, pady=2)
        ctk.CTkCheckBox(left, text="White Background",
                        variable=self.white_background).pack(anchor="w",
                                                              padx=20, pady=2)
        ctk.CTkCheckBox(left, text="Auto Enhance",
                        variable=self.auto_enhance).pack(anchor="w",
                                                         padx=20, pady=2)

        self.generate_button = ctk.CTkButton(left, text="Generate",
                                             command=self.generate_sheet,
                                             width=220)
        self.generate_button.pack(pady=10)

        self.print_button = ctk.CTkButton(left, text="Print",
                                          state="disabled",
                                          command=self.print_sheet, width=220)
        self.print_button.pack(pady=5)

        ctk.CTkButton(left, text="Exit",
                      fg_color="red", command=self.destroy, width=220).pack(pady=5)

        self.preview = ctk.CTkLabel(right, text="No Image Selected")
        self.preview.pack(fill="both", expand=True, padx=10, pady=10)

    # ── single-customer handlers ──────────────────────────────────────────────

    def open_photo(self):
        f = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if not f:
            return
        self.selected_image = f
        self.working_image  = Image.open(f).convert("RGB")
        self._refresh_preview(self.working_image)

    def rotate_photo(self, degrees):
        """Rotate the currently loaded photo 90° left or right."""
        if self.working_image is None:
            return
        # PIL rotate() is counter-clockwise for positive angles;
        # negate so "Rotate Right" visually rotates clockwise.
        self.working_image = self.working_image.rotate(-degrees, expand=True)
        self._refresh_preview(self.working_image)

    def _refresh_preview(self, pil_img):
        img = pil_img.copy()
        img.thumbnail((850, 620))
        cimg = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.preview.configure(image=cimg, text="")
        self.preview.image = cimg

    def generate_sheet(self):
        if self.working_image is None:
            return

        # Save the (possibly rotated) working image to a temp file
        # so the existing pipeline (which takes a file path) can use it.
        temp_input = os.path.join(tempfile.gettempdir(), "passport_input.jpg")
        self.working_image.save(temp_input, quality=100)

        copies = int(self.photo_count.get())
        sheet = generate_passport_sheet(
            image_path=temp_input,
            copies=copies,
            smart_crop=self.face_detection.get(),
            white_background=self.white_background.get(),
            enhance=self.auto_enhance.get()
        )

        self.generated_sheet = sheet
        temp_file = os.path.join(tempfile.gettempdir(), "passport_preview.jpg")
        sheet.save(temp_file, quality=100)

        image = Image.open(temp_file)
        image.thumbnail((850, 620))
        ctk_image = ctk.CTkImage(light_image=image, dark_image=image,
                                  size=image.size)
        self.preview.configure(image=ctk_image, text="")
        self.preview.image = ctk_image
        self.print_button.configure(state="normal")
        self.generate_button.configure(text="Regenerate")

    def print_sheet(self):
        if self.generated_sheet is None:
            return
        try:
            print_image(self.generated_sheet)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    app = PassportStudioApp()
    app.mainloop()
