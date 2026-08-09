import os
import threading
from tkinter import filedialog, messagebox
from PIL import Image
import customtkinter as ctk
from core.batch_engine import generate_batch
from core.printer import print_image

THUMB_W, THUMB_H = 80, 100
PREVIEW_MAX = (760, 580)
MIN_COPIES = 1
MAX_COPIES = 48


def _thumb(path):
    try:
        img = Image.open(path)
        img.thumbnail((THUMB_W, THUMB_H))
        return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:
        return None


class CustomerCard(ctk.CTkFrame):
    def __init__(self, master, index, on_remove, **kw):
        super().__init__(master, corner_radius=8, **kw)
        self.index = index
        self.on_remove = on_remove
        self.image_path = None
        self._copies = 12
        self._build()

    def _build(self):
        # ── thumbnail
        self.thumb_label = ctk.CTkLabel(self, text="No\nPhoto",
                                        width=THUMB_W, height=THUMB_H,
                                        fg_color=("gray80", "gray25"),
                                        corner_radius=6)
        self.thumb_label.grid(row=0, column=0, rowspan=3, padx=(8, 6), pady=8)

        # ── customer name
        self.num_label = ctk.CTkLabel(self, text=f"Customer {self.index + 1}",
                                      font=("Segoe UI", 13, "bold"))
        self.num_label.grid(row=0, column=1, sticky="w", padx=4, pady=(8, 0))

        # ── file name
        self.file_label = ctk.CTkLabel(self, text="No photo selected",
                                       text_color="gray60",
                                       font=("Segoe UI", 11))
        self.file_label.grid(row=1, column=1, sticky="w", padx=4)

        # ── +/- copies control
        copies_frame = ctk.CTkFrame(self, fg_color="transparent")
        copies_frame.grid(row=2, column=1, sticky="w", padx=4, pady=(2, 8))

        ctk.CTkLabel(copies_frame, text="Photos:",
                     font=("Segoe UI", 12)).pack(side="left", padx=(0, 6))

        ctk.CTkButton(copies_frame, text="−", width=32, height=32,
                      font=("Segoe UI", 16, "bold"),
                      command=self._decrease).pack(side="left")

        self.copies_label = ctk.CTkLabel(copies_frame, text=str(self._copies),
                                         width=40, height=32,
                                         font=("Segoe UI", 14, "bold"),
                                         fg_color=("gray80", "gray25"),
                                         corner_radius=6)
        self.copies_label.pack(side="left", padx=4)

        ctk.CTkButton(copies_frame, text="+", width=32, height=32,
                      font=("Segoe UI", 16, "bold"),
                      command=self._increase).pack(side="left")

        # ── quick preset buttons
        preset_frame = ctk.CTkFrame(self, fg_color="transparent")
        preset_frame.grid(row=2, column=2, sticky="w", padx=8, pady=(2, 8))

        ctk.CTkLabel(preset_frame, text="Quick:",
                     font=("Segoe UI", 11),
                     text_color="gray60").pack(side="left", padx=(0, 4))

        for val in [6, 12, 18, 24]:
            ctk.CTkButton(preset_frame, text=str(val),
                          width=36, height=28,
                          font=("Segoe UI", 11),
                          fg_color=("gray70", "gray30"),
                          hover_color=("gray55", "gray45"),
                          command=lambda v=val: self._set_copies(v)).pack(side="left", padx=2)

        # ── processing options
        opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        opt_frame.grid(row=0, column=2, rowspan=2, padx=8, pady=6, sticky="ns")

        self.smart_crop_var = ctk.BooleanVar(value=True)
        self.white_bg_var   = ctk.BooleanVar(value=False)
        self.enhance_var    = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(opt_frame, text="Smart Crop",
                        variable=self.smart_crop_var, width=130).pack(anchor="w", pady=1)
        ctk.CTkCheckBox(opt_frame, text="White BG",
                        variable=self.white_bg_var, width=130).pack(anchor="w", pady=1)
        ctk.CTkCheckBox(opt_frame, text="Auto Enhance",
                        variable=self.enhance_var, width=130).pack(anchor="w", pady=1)

        # ── action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=3, rowspan=3, padx=(4, 8), pady=6, sticky="ns")

        ctk.CTkButton(btn_frame, text="📂 Photo", width=95,
                      command=self._browse).pack(pady=2)
        ctk.CTkButton(btn_frame, text="✖ Remove", width=95,
                      fg_color="#c0392b", hover_color="#922b21",
                      command=lambda: self.on_remove(self)).pack(pady=2)

        self.columnconfigure(1, weight=1)

    # ── copies controls

    def _increase(self):
        if self._copies < MAX_COPIES:
            self._copies += 1
            self.copies_label.configure(text=str(self._copies))

    def _decrease(self):
        if self._copies > MIN_COPIES:
            self._copies -= 1
            self.copies_label.configure(text=str(self._copies))

    def _set_copies(self, value):
        self._copies = value
        self.copies_label.configure(text=str(self._copies))

    # ── photo browse

    def _browse(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if not path:
            return
        self.image_path = path
        self.file_label.configure(text=os.path.basename(path))
        t = _thumb(path)
        if t:
            self.thumb_label.configure(image=t, text="")
            self.thumb_label.image = t

    def to_dict(self):
        return {
            "image_path":       self.image_path,
            "copies":           self._copies,
            "smart_crop":       self.smart_crop_var.get(),
            "white_background": self.white_bg_var.get(),
            "enhance":          self.enhance_var.get(),
            "label":            self.num_label.cget("text"),
        }

    def renumber(self, new_index):
        self.index = new_index
        self.num_label.configure(text=f"Customer {new_index + 1}")


class BatchTab(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._cards = []
        self._results = []
        self._combined_sheet = None
        self._preview_index = 0
        self._build()

    def _build(self):
        left = ctk.CTkFrame(self, width=480)
        left.pack(side="left", fill="y", padx=(6, 4), pady=6)
        left.pack_propagate(False)
        right = ctk.CTkFrame(self)
        right.pack(side="right", fill="both", expand=True, padx=(4, 6), pady=6)
        self._build_left(left)
        self._build_right(right)

    def _build_left(self, parent):
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkButton(toolbar, text="➕ Add Customer",
                      command=self._add_card, width=160).pack(side="left")
        ctk.CTkButton(toolbar, text="🗑 Clear All",
                      fg_color="#7f8c8d", hover_color="#626567",
                      command=self._clear_all, width=110).pack(side="left", padx=6)

        self.scroll = ctk.CTkScrollableFrame(parent, label_text="Customers")
        self.scroll.pack(fill="both", expand=True, padx=8, pady=4)

        action_bar = ctk.CTkFrame(parent, fg_color="transparent")
        action_bar.pack(fill="x", padx=8, pady=(4, 8))
        self.gen_btn = ctk.CTkButton(action_bar, text="⚙ Generate All",
                                     command=self._generate_all, width=175)
        self.gen_btn.pack(side="left")
        self.print_all_btn = ctk.CTkButton(action_bar, text="🖨 Print All",
                                           fg_color="#1a6b3c", hover_color="#14532d",
                                           state="disabled", command=self._print_all,
                                           width=130)
        self.print_all_btn.pack(side="left", padx=6)

        self.status_label = ctk.CTkLabel(parent, text="", text_color="gray60",
                                         font=("Segoe UI", 11))
        self.status_label.pack(pady=(0, 4))

    def _build_right(self, parent):
        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.pack(fill="x", padx=8, pady=(8, 2))
        self.prev_btn = ctk.CTkButton(nav, text="◀ Prev", width=80,
                                      state="disabled", command=self._prev_preview)
        self.prev_btn.pack(side="left")
        self.preview_title = ctk.CTkLabel(nav, text="Preview",
                                          font=("Segoe UI", 14, "bold"))
        self.preview_title.pack(side="left", expand=True)
        self.next_btn = ctk.CTkButton(nav, text="Next ▶", width=80,
                                      state="disabled", command=self._next_preview)
        self.next_btn.pack(side="right")

        self.preview_label = ctk.CTkLabel(parent, text="Generate to see preview",
                                          fg_color=("gray85", "gray20"),
                                          corner_radius=10)
        self.preview_label.pack(fill="both", expand=True, padx=8, pady=(2, 4))

        self.print_one_btn = ctk.CTkButton(parent, text="🖨 Print This Sheet",
                                           fg_color="#1a6b3c", hover_color="#14532d",
                                           state="disabled", command=self._print_current)
        self.print_one_btn.pack(pady=(2, 4))

        self.save_btn = ctk.CTkButton(parent, text="💾 Save Sheet",
                                      fg_color="#2471a3", hover_color="#1a5276",
                                      state="disabled", command=self._save_all)
        self.save_btn.pack(pady=(0, 8))

    # ── card management

    def _add_card(self):
        card = CustomerCard(self.scroll, index=len(self._cards),
                            on_remove=self._remove_card)
        card.pack(fill="x", padx=4, pady=4)
        self._cards.append(card)
        self._set_status(f"{len(self._cards)} customer(s) added")

    def _remove_card(self, card):
        card.pack_forget()
        card.destroy()
        self._cards.remove(card)
        for i, c in enumerate(self._cards):
            c.renumber(i)
        self._set_status(f"{len(self._cards)} customer(s)")

    def _clear_all(self):
        for c in list(self._cards):
            c.pack_forget()
            c.destroy()
        self._cards.clear()
        self._results.clear()
        self._reset_preview()
        self._set_status("Cleared")

    # ── generation

    def _generate_all(self):
        if not self._cards:
            messagebox.showwarning("No Customers", "Please add at least one customer.")
            return
        missing = [c.index + 1 for c in self._cards if not c.image_path]
        if missing:
            messagebox.showerror("Missing Photos",
                                 f"Customer(s) {', '.join(map(str, missing))} have no photo.")
            return

        customers = [c.to_dict() for c in self._cards]
        self.gen_btn.configure(state="disabled", text="⏳ Generating…")
        self.print_all_btn.configure(state="disabled")
        self.print_one_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self._set_status("Processing…")

        def _worker():
            result = generate_batch(customers)
            self.after(0, lambda: self._on_generated(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_generated(self, result):
        self._combined_sheet = result["combined_sheet"]
        errors = result["errors"]

        self.gen_btn.configure(state="normal", text="⚙ Generate All")

        if errors:
            messagebox.showerror("Some customers failed",
                                 "\n".join(f"• {e['label']}: {e['error']}" for e in errors))

        if self._combined_sheet:
            self.print_all_btn.configure(state="normal")
            self.print_one_btn.configure(state="normal")
            self.save_btn.configure(state="normal")
            self._show_combined_preview()
            self._set_status("✅ Sheet ready"
                             + (f" | ❌ {len(errors)} failed" if errors else ""))
        else:
            self._reset_preview()
            self._set_status("❌ All customers failed")

    # ── preview

    def _show_combined_preview(self):
        if not self._combined_sheet:
            return
        img = self._combined_sheet.copy()
        img.thumbnail(PREVIEW_MAX, Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.preview_label.configure(image=ctk_img, text="")
        self.preview_label.image = ctk_img
        self.preview_title.configure(text="Combined Sheet Preview")
        self.prev_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")

    def _prev_preview(self):
        pass

    def _next_preview(self):
        pass

    def _reset_preview(self):
        self._combined_sheet = None
        self.preview_label.configure(image=None, text="Generate to see preview")
        self.preview_label.image = None
        self.preview_title.configure(text="Preview")
        self.prev_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self.print_all_btn.configure(state="disabled")
        self.print_one_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")

    # ── print / save

    def _print_current(self):
        if not self._combined_sheet:
            return
        try:
            print_image(self._combined_sheet)
            self._set_status("🖨 Sent to printer")
        except Exception as exc:
            messagebox.showerror("Print Error", str(exc))

    def _print_all(self):
        if not self._combined_sheet:
            return
        if not messagebox.askyesno("Print", "Send the combined sheet to the printer?"):
            return

        def _worker():
            try:
                print_image(self._combined_sheet)
                self.after(0, lambda: self._set_status("✅ Sent to printer"))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Print Error", str(exc)))

        threading.Thread(target=_worker, daemon=True).start()
        self._set_status("🖨 Printing…")

    def _save_all(self):
        if not self._combined_sheet:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg")],
            initialfile="combined_sheet.jpg",
            title="Save Combined Sheet"
        )
        if not path:
            return
        try:
            self._combined_sheet.save(path, quality=100)
            messagebox.showinfo("Saved", f"Saved to:\n{path}")
            self._set_status("💾 Sheet saved")
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))

    def _set_status(self, msg):
        self.status_label.configure(text=msg)