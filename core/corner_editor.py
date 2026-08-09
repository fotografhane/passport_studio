import tkinter as tk
from PIL import Image, ImageTk


class CornerEditor(tk.Canvas):
    """
    Interactive canvas that shows an image with 4 draggable corner
    handles + connecting lines. Lets the user fine-tune auto-detected
    document corners before cropping.

    Usage:
        editor = CornerEditor(parent, width=700, height=550)
        editor.pack(fill="both", expand=True)
        editor.load_image(pil_image, corners_in_image_coords)
        ...
        corners = editor.get_corners_in_image_coords()
    """

    HANDLE_RADIUS = 12
    HANDLE_COLOR = "#ff3b30"
    HANDLE_ACTIVE_COLOR = "#ffcc00"
    LINE_COLOR = "#00e676"

    def __init__(self, master, width=700, height=550, **kw):
        super().__init__(master, width=width, height=height,
                         bg="#1a1a1a", highlightthickness=0, **kw)
        self.pil_image = None
        self.tk_image = None
        self.img_id = None

        self.display_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.corners_display = []   # canvas-space coordinates
        self.handle_ids = []
        self.line_id = None

        self._dragging_idx = None

        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ── public API ───────────────────────────────────────────────────────────

    def load_image(self, pil_image: Image.Image, corners_image_coords):
        """
        pil_image: original full-resolution PIL image
        corners_image_coords: numpy array / list of 4 (x, y) points
                              in the ORIGINAL image's pixel coordinates,
                              order: TL, TR, BR, BL
        """
        self.pil_image = pil_image
        self.delete("all")

        canvas_w = max(self.winfo_width(), 400)
        canvas_h = max(self.winfo_height(), 400)

        img_w, img_h = pil_image.size
        scale = min((canvas_w - 20) / img_w, (canvas_h - 20) / img_h)
        self.display_scale = scale

        disp_w = int(img_w * scale)
        disp_h = int(img_h * scale)

        self.offset_x = (canvas_w - disp_w) // 2
        self.offset_y = (canvas_h - disp_h) // 2

        display_img = pil_image.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display_img)
        self.img_id = self.create_image(self.offset_x, self.offset_y,
                                         anchor="nw", image=self.tk_image)

        # Convert corners to canvas-display coordinates
        self.corners_display = []
        for (x, y) in corners_image_coords:
            cx = x * scale + self.offset_x
            cy = y * scale + self.offset_y
            self.corners_display.append([cx, cy])

        self._draw_overlay()

    def get_corners_in_image_coords(self):
        """Return the 4 corners converted back to original image pixel coords."""
        pts = []
        for (cx, cy) in self.corners_display:
            x = (cx - self.offset_x) / self.display_scale
            y = (cy - self.offset_y) / self.display_scale
            pts.append([x, y])
        return pts

    def reset_corners(self, corners_image_coords):
        """Update corner positions (e.g. after re-running auto-detect)."""
        self.corners_display = []
        for (x, y) in corners_image_coords:
            cx = x * self.display_scale + self.offset_x
            cy = y * self.display_scale + self.offset_y
            self.corners_display.append([cx, cy])
        self._draw_overlay()

    # ── drawing ──────────────────────────────────────────────────────────────

    def _draw_overlay(self):
        for hid in self.handle_ids:
            self.delete(hid)
        if self.line_id:
            self.delete(self.line_id)
        self.handle_ids = []

        if len(self.corners_display) != 4:
            return

        # Connecting polygon
        flat = []
        for (x, y) in self.corners_display + [self.corners_display[0]]:
            flat.extend([x, y])
        self.line_id = self.create_line(*flat, fill=self.LINE_COLOR,
                                        width=3, tags="overlay")

        # Draggable handles
        for i, (x, y) in enumerate(self.corners_display):
            r = self.HANDLE_RADIUS
            hid = self.create_oval(x - r, y - r, x + r, y + r,
                                   fill=self.HANDLE_COLOR,
                                   outline="white", width=2,
                                   tags=(f"handle_{i}", "handle"))
            self.handle_ids.append(hid)

    # ── drag handlers ────────────────────────────────────────────────────────

    def _on_press(self, event):
        for i, (x, y) in enumerate(self.corners_display):
            if (event.x - x) ** 2 + (event.y - y) ** 2 <= (self.HANDLE_RADIUS + 8) ** 2:
                self._dragging_idx = i
                self.itemconfig(self.handle_ids[i], fill=self.HANDLE_ACTIVE_COLOR)
                return

    def _on_drag(self, event):
        if self._dragging_idx is None:
            return
        i = self._dragging_idx

        # Clamp to canvas/image bounds
        x = max(self.offset_x, min(event.x, self.offset_x + self.pil_image.size[0] * self.display_scale))
        y = max(self.offset_y, min(event.y, self.offset_y + self.pil_image.size[1] * self.display_scale))

        self.corners_display[i] = [x, y]
        self._draw_overlay()

    def _on_release(self, event):
        if self._dragging_idx is not None:
            self.itemconfig(self.handle_ids[self._dragging_idx],
                           fill=self.HANDLE_COLOR)
        self._dragging_idx = None