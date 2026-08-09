import cv2
import numpy as np


def order_points(pts):
    """Order points: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _four_point_from_contour(c):
    """Try to reduce a contour to 4 points; fall back to minAreaRect."""
    peri = cv2.arcLength(c, True)
    for eps_factor in [0.02, 0.03, 0.05, 0.08]:
        approx = cv2.approxPolyDP(c, eps_factor * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2)
    rect = cv2.minAreaRect(c)
    return cv2.boxPoints(rect)


def detect_document(image):
    """
    Detect document edges using multiple strategies (Canny at several
    thresholds, adaptive threshold, Otsu threshold) and pick the best
    candidate. Works across varied backgrounds and lighting.

    Returns ordered 4 corner points (float32 array) or None if nothing
    plausible is found at all.
    """
    orig_h, orig_w = image.shape[:2]
    scale = 1000 / max(orig_h, orig_w)
    resized = cv2.resize(image, (int(orig_w * scale), int(orig_h * scale)))
    rh, rw = resized.shape[:2]
    total_area = rh * rw

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    candidates = []

    # ── Strategy 1: Canny edges at multiple blur/threshold combos
    for blur_k in [5, 7]:
        blurred = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)
        for lo, hi in [(30, 100), (20, 80), (50, 150), (10, 50)]:
            edged = cv2.Canny(blurred, lo, hi)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
            edged = cv2.dilate(edged, kernel, iterations=2)
            edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:3]
            for c in contours:
                area = cv2.contourArea(c)
                if 0.15 * total_area < area < 0.95 * total_area:
                    candidates.append((area, _four_point_from_contour(c)))

    # ── Strategy 2: Adaptive threshold (good for paper on varied backgrounds)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 25, 10)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:3]
    for c in contours:
        area = cv2.contourArea(c)
        if 0.15 * total_area < area < 0.95 * total_area:
            candidates.append((area, _four_point_from_contour(c)))

    # ── Strategy 3: Otsu threshold for bright paper region
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed2 = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed2, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:3]
    for c in contours:
        area = cv2.contourArea(c)
        if 0.15 * total_area < area < 0.95 * total_area:
            candidates.append((area, _four_point_from_contour(c)))

    if not candidates:
        return None

    # Pick the largest-area candidate as the best guess
    candidates.sort(key=lambda x: -x[0])
    best_pts = candidates[0][1]

    pts_orig = best_pts.astype("float32") / scale

    # Clamp to image bounds
    pts_orig[:, 0] = np.clip(pts_orig[:, 0], 0, orig_w - 1)
    pts_orig[:, 1] = np.clip(pts_orig[:, 1], 0, orig_h - 1)

    return order_points(pts_orig)


def default_corners(image_w, image_h, margin_pct=0.08):
    """
    Fallback corners when auto-detect finds nothing —
    a rectangle slightly inset from the full image, so the
    user always has something to drag/adjust from.
    """
    mx = int(image_w * margin_pct)
    my = int(image_h * margin_pct)
    pts = np.array([
        [mx, my],
        [image_w - mx, my],
        [image_w - mx, image_h - my],
        [mx, image_h - my],
    ], dtype="float32")
    return pts


def draw_detected_corners(image, pts):
    """Draw detected document corners on image for preview (static, non-interactive)."""
    preview = image.copy()
    pts_int = pts.astype(int)
    cv2.polylines(preview, [pts_int], True, (0, 255, 0), 3)
    for pt in pts_int:
        cv2.circle(preview, tuple(pt), 10, (0, 0, 255), -1)
    return preview