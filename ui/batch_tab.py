import os
import threading
import tempfile
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

from core.batch_engine import generate_batch
from core.printer import print_image


# ── constants ────────────────────────────────────────────────────────────────

THUMB_W, THUMB_H = 70, 88
PREVIEW_MAX = (760, 580)
MIN_COPIES = 1
MAX_COPIES = 48
QUICK_VALUES = [6, 12, 18, 24]

COLOR_SELECTED = "#2fa572"
COLOR_SELECTED_HOVER = "#238a5c"
COLOR_UNSELECTED = "#3a3a3a"
COLOR_UNSELECTED_HOVER = "#4a4a4a"


def _thumb(path: str):
    try:
        img = Image.open(path)
        img.thumbnail((THUMB_W, THUMB_H))
        return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:
        return None


# ── customer card ────────────────────────────────────────────────────────────

class CustomerCard(ctk.CTkFrame):
    """One row in the customer list — clean stacked layout, no overlap."""

    def __init__(self, master, index: int, on_remove, **kw):
        super().__init__(master, corner_radius=8, **kw)
        self.index = index
        self.on_remove = on_remove
        self.image_path: str | None = None
        self._copies = 12
        self.qty_buttons = {}

        self._build()

    def _build(self):
        # ── Row A: thumbnail (left) + filename/checkboxes (right)
        row_a = ctk.CTkFrame(self, fg_color="transparent")
        row_a.pack(fill="x", padx=8, pady=(8, 4))

        self.thumb_label = ctk.CTkLabel(row_a, text="No\nPhoto",
                                        width=THUMB_W, height=THUMB_H,
                                        fg_color=("gray80", "gray25"),
                                        corner_radius=6)
        self.thumb_label.pack(side="left", padx=(0, 10))

        info_col = ctk.CTkFrame(row_a, fg_color="transparent")
        info_col.pack(side="left", fill="both", expand=True)

        self.file_label = ctk.CTkLabel(
            info_col,
            text=f"Customer {self.index + 1}  ·  No photo selected",
            font=("Segoe UI", 12, "bold"),
            anchor="w", justify="left")
        self.file_label.pack(fill="x", pady=(2, 6))

        check_row = ctk.CTkFrame(info_col, fg_color="transparent")
        check_row.pack(fill="x")

        self.smart_crop_var = ctk.BooleanVar(value=True)
        self.white_bg_var   = ctk.BooleanVar(value=False)
        self.enhance_var    = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(check_row, text="Smart Crop", width=20,
                        variable=self.smart_crop_var,
                        font=("Segoe UI", 11)).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(check_row, text="White BG", width=20,
                        variable=self.white_bg_var,
                        font=("Segoe UI", 11)).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(check_row, text="Auto Enhance", width=20,
                        variable=self.enhance_var,
                        font=("Segoe UI", 11)).pack(side="left")

        # ── Row B: photo count — quick buttons (highlighted) + fine adjust
        row_b = ctk.CTkFrame(self, fg_color="transparent")
        row_b.pack(fill="x", padx=8, pady=(2, 4))

        ctk.CTkLabel(row_b, text="Photos:",
                     font=("Segoe UI", 12)).pack(side="left", padx=(0, 8))

        for val in QUICK_VALUES:
            btn = ctk.CTkButton(row_b, text=str(val), width=42, height=30,
                                font=("Segoe UI", 12, "bold"),
                                fg_color=COLOR_UNSELECTED,
                                hover_color=COLOR_UNSELECTED_HOVER,
                                command=lambda v=val: self._set_copies(v))
            btn.pack(side="left", padx=3)
            self.qty_buttons[val] = btn

        fine_frame = ctk.CTkFrame(row_b, fg_color="transparent")
        fine_frame.pack(side="left", padx=(14, 0))

        ctk.CTkButton(fine_frame, text="−", width=28, height=30,
                      font=("Segoe UI", 14, "bold"),
                      command=self._decrease).pack(side="left")

        self.copies_display = ctk.CTkLabel(fine_frame, text=str(self._copies),
                                           width=34, height=30,
                                           font=("Segoe UI", 12, "bold"),
                                           fg_color=("gray80", "gray25"),
                                           corner_radius=6)
        self.copies_display.pack(side="left", padx=3)

        ctk.CTkButton(fine_frame, text="+", width=28, height=30,
                      font=("Segoe UI", 14, "bold"),
                      command=self._increase).pack(side="left")

        # ── Row C: action buttons
        row_c = ctk.CTkFrame(self, fg_color="transparent")
        row_c.pack(fill="x", padx=8, pady=(4, 8))

        ctk.CTkButton(row_c, text="📂 Select Photo", width=140, height=30,
                      command=self._browse).pack(side="left")
        ctk.CTkButton(row_c, text="✖ Remove", width=100, height=30,
                      fg_color="#c0392b", hover_color="#922b21",
                      command=lambda: self.on_remove(self)).pack(side="right")

        self._refresh_highlight()

    # ── behavior ─────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if not path:
            return
        self.image_path = path
        self.file_label.configure(
            text=f"Customer {self.index + 1}  ·  {os.path.basename(path)}")
        t = _thumb(path)
        if t:
            self.thumb_label.configure(image=t, text="")
            self.thumb_label.image = t

    def _set_copies(self, value):
        self._copies = value
        self.copies_display.configure(text=str(self._copies))
        self._refresh_highlight()

    def _increase(self):
        if self._copies < MAX_COPIES:
            self._copies += 1
            self.copies_display.configure(text=str(self._copies))
            self._refresh_highlight()

    def _decrease(self):
        if self._copies > MIN_COPIES:
            self._copies -= 1
            self.copies_display.configure(text=str(self._copies))
            self._refresh_highlight()

    def _refresh_highlight(self):
        """Highlight the quick-select button matching the current count."""
        for val, btn in self.qty_buttons.items():
            if val == self._copies:
                btn.configure(fg_color=COLOR_SELECTED,
                             hover_color=COLOR_SELECTED_HOVER)
            else:
                btn.configure(fg_color=COLOR_UNSELECTED,
                             hover_color=COLOR_UNSELECTED_HOVER)

    def to_dict(self) -> dict:
        return {
            "image_path":       self.image_path,
            "copies":           self._copies,
            "smart_crop":       self.smart_crop_var.get(),
            "white_background": self.white_bg_var.get(),
            "enhance":          self.enhance_var.get(),
            "label":            f"Customer {self.index + 1}",
        }

    def renumber(self, new_index: int):
        self.index = new_index
        name = os.path.basename(self.image_path) if self.image_path else "No photo selected"
        self.file_label.configure(text=f"Customer {new_index + 1}  ·  {name}")


# ── main batch tab ───────────────────────────────────────────────────────────

class BatchTab(ctk.CTkFrame):
    """
    Drop this frame into a CTkTabview tab.

        tab = tabview.add("Batch")
        BatchTab(tab).pack(fill="both", expand=True)
    """

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._cards: list[CustomerCard] = []
        self._results: list[dict] = []
        self._preview_index: int = 0

        self._build()

    # ── layout ──────────────────────────────────────────────────────────────

    def _build(self):
        left = ctk.CTkFrame(self, width=460)
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

        self.print_all_btn = ctk.CTkButton(
            action_bar, text="🖨 Print All",
            fg_color="#1a6b3c", hover_color="#14532d",
            state="disabled", command=self._print_all, width=130)
        self.print_all_btn.pack(side="left", padx=6)

        self.status_label = ctk.CTkLabel(parent, text="",
                                         text_color="gray60",
                                         font=("Segoe UI", 11))
        self.status_label.pack(pady=(0, 4))

    def _build_right(self, parent):
        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.pack(fill="x", padx=8, pady=(8, 2))

        self.prev_btn = ctk.CTkButton(nav, text="◀ Prev", width=80,
                                      state="disabled",
                                      command=self._prev_preview)
        self.prev_btn.pack(side="left")

        self.preview_title = ctk.CTkLabel(nav, text="Preview",
                                          font=("Segoe UI", 14, "bold"))
        self.preview_title.pack(side="left", expand=True)

        self.next_btn = ctk.CTkButton(nav, text="Next ▶", width=80,
                                      state="disabled",
                                      command=self._next_preview)
        self.next_btn.pack(side="right")

        self.preview_label = ctk.CTkLabel(parent, text="Generate to see preview",
                                          fg_color=("gray85", "gray20"),
                                          corner_radius=10)
        self.preview_label.pack(fill="both", expand=True, padx=8, pady=(2, 4))

        self.print_one_btn = ctk.CTkButton(
            parent, text="🖨 Print This Sheet",
            fg_color="#1a6b3c", hover_color="#14532d",
            state="disabled", command=self._print_current)
        self.print_one_btn.pack(pady=(2, 8))

        self.save_btn = ctk.CTkButton(
            parent, text="💾 Save All Sheets",
            fg_color="#2471a3", hover_color="#1a5276",
            state="disabled", command=self._save_all)
        self.save_btn.pack(pady=(0, 8))

    # ── card management ─────────────────────────────────────────────────────

    def _add_card(self):
        card = CustomerCard(self.scroll, index=len(self._cards),
                            on_remove=self._remove_card)
        card.pack(fill="x", padx=4, pady=4)
        self._cards.append(card)
        self._set_status(f"{len(self._cards)} customer(s) added")

    def _remove_card(self, card: CustomerCard):
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

    # ── generation ──────────────────────────────────────────────────────────

    def _generate_all(self):
        if not self._cards:
            messagebox.showwarning("No Customers",
                                   "Please add at least one customer.")
            return

        missing = [c.index + 1 for c in self._cards if not c.image_path]
        if missing:
            nums = ", ".join(str(n) for n in missing)
            messagebox.showerror("Missing Photos",
                                 f"Customer(s) {nums} have no photo selected.")
            return

        customers = [c.to_dict() for c in self._cards]

        self.gen_btn.configure(state="disabled", text="⏳ Generating…")
        self.print_all_btn.configure(state="disabled")
        self.print_one_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self._set_status("Processing…")

        def _worker():
            results = generate_batch(customers)
            self.after(0, lambda: self._on_generated(results))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_generated(self, results):
        # generate_batch may return either a dict {"combined_sheet":..,"errors":..}
        # or a list of per-customer results depending on which batch_engine
        # version is in use — handle both gracefully.
        if isinstance(results, dict):
            self._results = [results] if results.get("combined_sheet") else []
            errors = results.get("errors", [])
        else:
            self._results = results
            errors = [r for r in results if r.get("error")]

        self.gen_btn.configure(state="normal", text="⚙ Generate All")

        valid = self._valid_results()

        if errors:
            msgs = "\n".join(
                f"• {e.get('label','?')}: {e.get('error','?')}" for e in errors)
            messagebox.showerror("Some sheets failed", msgs)

        if valid:
            self.print_all_btn.configure(state="normal")
            self.print_one_btn.configure(state="normal")
            self.save_btn.configure(state="normal")
            self._preview_index = 0
            self._show_preview(0)
            self._set_status(
                f"✅ {len(valid)} sheet(s) ready"
                + (f" | ❌ {len(errors)} failed" if errors else ""))
        else:
            self._reset_preview()
            self._set_status("❌ All sheets failed")

    # ── preview ──────────────────────────────────────────────────────────────

    def _valid_results(self):
        out = []
        for r in self._results:
            sheet = r.get("sheet") or r.get("combined_sheet")
            if sheet is not None:
                out.append(r)
        return out

    def _get_sheet(self, r):
        return r.get("sheet") or r.get("combined_sheet")

    def _show_preview(self, idx: int):
        valid = self._valid_results()
        if not valid:
            return

        idx = max(0, min(idx, len(valid) - 1))
        self._preview_index = idx
        r = valid[idx]
        sheet = self._get_sheet(r)

        img = sheet.copy()
        img.thumbnail(PREVIEW_MAX, Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.preview_label.configure(image=ctk_img, text="")
        self.preview_label.image = ctk_img

        label = r.get("label", "Sheet")
        copies = r.get("copies", "")
        extra = f"  ({copies} photos)" if copies else ""
        self.preview_title.configure(
            text=f"{label}{extra}  [{idx + 1}/{len(valid)}]")

        self.prev_btn.configure(state="normal" if idx > 0 else "disabled")
        self.next_btn.configure(state="normal" if idx < len(valid) - 1 else "disabled")

    def _prev_preview(self):
        self._show_preview(self._preview_index - 1)

    def _next_preview(self):
        self._show_preview(self._preview_index + 1)

    def _reset_preview(self):
        self.preview_label.configure(image=None,
                                     text="Generate to see preview")
        self.preview_label.image = None
        self.preview_title.configure(text="Preview")
        self.prev_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self.print_all_btn.configure(state="disabled")
        self.print_one_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")

    # ── printing ─────────────────────────────────────────────────────────────

    def _print_current(self):
        valid = self._valid_results()
        if not valid:
            return
        r = valid[self._preview_index]
        try:
            print_image(self._get_sheet(r))
            self._set_status(f"🖨 Sent: {r.get('label', 'sheet')}")
        except Exception as exc:
            messagebox.showerror("Print Error", str(exc))

    def _print_all(self):
        valid = self._valid_results()
        if not valid:
            return

        if not messagebox.askyesno(
                "Print All",
                f"Send {len(valid)} sheet(s) to the printer?"):
            return

        def _worker():
            for r in valid:
                try:
                    print_image(self._get_sheet(r))
                except Exception as exc:
                    self.after(0, lambda e=str(exc), lbl=r.get('label', '?'):
                               messagebox.showerror("Print Error",
                                                    f"{lbl}: {e}"))
            self.after(0, lambda: self._set_status(
                f"✅ Sent {len(valid)} sheet(s) to printer"))

        threading.Thread(target=_worker, daemon=True).start()
        self._set_status("🖨 Printing…")

    # ── save ─────────────────────────────────────────────────────────────────

    def _save_all(self):
        valid = self._valid_results()
        if not valid:
            return

        folder = filedialog.askdirectory(title="Select folder to save sheets")
        if not folder:
            return

        saved, failed = 0, 0
        for r in valid:
            label = r.get("label", "sheet")
            safe_name = label.replace(" ", "_").replace("/", "-")
            out_path = os.path.join(folder, f"{safe_name}.jpg")
            try:
                self._get_sheet(r).save(out_path, quality=100)
                saved += 1
            except Exception:
                failed += 1

        msg = f"Saved {saved} sheet(s) to:\n{folder}"
        if failed:
            msg += f"\n({failed} failed)"
        messagebox.showinfo("Saved", msg)
        self._set_status(f"💾 Saved {saved} sheet(s)")

    # ── misc ──────────────────────────────────────────────────────────────────

    def _set_status(self, msg: str):
        self.status_label.configure(text=msg)