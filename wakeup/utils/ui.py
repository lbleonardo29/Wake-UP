# utils/ui.py — Renderizado de la interfaz con fuentes TrueType (Pillow)
#
# OpenCV solo trae las fuentes Hershey (vectoriales y bloquosas). Para una
# interfaz más limpia usamos Pillow, que renderiza fuentes TrueType del sistema
# (Segoe UI en Windows) con antialiasing real.
#
# Estrategia de dibujo:
#   - Convertimos el frame BGR (OpenCV) a una imagen RGBA (Pillow).
#   - Dibujamos TODO sobre una capa transparente: paneles translúcidos (alpha
#     bajo) y texto opaco (alpha 255), respetando el orden de llamada.
#   - Componemos la capa sobre el frame una sola vez y regresamos a BGR.

import os
import cv2
import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("[UI] Pillow no instalado, usando fuentes básicas de OpenCV")

# ── Paleta (RGB) ──
COL_PANEL   = (16, 18, 27)        # Fondo de paneles
COL_TEXT    = (236, 238, 245)     # Texto principal
COL_DIM     = (150, 156, 170)     # Texto secundario
COL_ACCENT  = (96, 165, 255)      # Azul de marca
COL_OK      = (74, 222, 128)      # Verde (alerta/despierto)
COL_WARN    = (251, 191, 36)      # Ámbar (ojos cerrados)
COL_DANGER  = (248, 80, 80)       # Rojo (somnoliento)

_FONT_CACHE = {}


def _font(size, bold=False):
    """Carga una fuente TrueType del sistema, con cache y fallbacks."""
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    win_fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    candidates = (
        ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
        if bold else
        ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
    )

    font = None
    for name in candidates:
        path = os.path.join(win_fonts, name)
        try:
            if os.path.exists(path):
                font = ImageFont.truetype(path, size)
                break
            font = ImageFont.truetype(name, size)  # busca en rutas del sistema
            break
        except Exception:
            continue

    if font is None:
        font = ImageFont.load_default()

    _FONT_CACHE[key] = font
    return font


class Overlay:
    """Acumula dibujos sobre una capa transparente y compone al final."""

    def __init__(self, frame):
        self.h, self.w = frame.shape[:2]
        if PIL_OK:
            self.base = Image.fromarray(
                cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ).convert("RGBA")
            self.layer = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
            self.d = ImageDraw.Draw(self.layer)
        else:
            self.frame = frame  # fallback OpenCV

    # ── Primitivas ──
    def panel(self, box, color=COL_PANEL, alpha=200, radius=14):
        if not PIL_OK:
            return
        self.d.rounded_rectangle(box, radius=radius, fill=(*color, alpha))

    def bar(self, box, color, alpha=255, radius=6):
        if not PIL_OK:
            return
        self.d.rounded_rectangle(box, radius=radius, fill=(*color, alpha))

    def line(self, p0, p1, color, width=2):
        if not PIL_OK:
            return
        self.d.line([p0, p1], fill=(*color, 255), width=width)

    def text(self, xy, s, size=20, bold=False, color=COL_TEXT,
             anchor="la", alpha=255):
        if not PIL_OK:
            x, y = xy
            cv2.putText(self.frame, s, (int(x), int(y) + size),
                        cv2.FONT_HERSHEY_SIMPLEX, size / 28.0,
                        (color[2], color[1], color[0]), 1, cv2.LINE_AA)
            return
        self.d.text(xy, s, font=_font(size, bold),
                    fill=(*color, alpha), anchor=anchor)

    def text_centered(self, cx, cy, s, size=40, bold=True, color=COL_TEXT,
                      alpha=255, shadow=True):
        if not PIL_OK:
            self.text((cx, cy), s, size, bold, color)
            return
        if shadow:
            self.d.text((cx + 2, cy + 2), s, font=_font(size, bold),
                        fill=(0, 0, 0, int(alpha * 0.6)), anchor="mm")
        self.d.text((cx, cy), s, font=_font(size, bold),
                    fill=(*color, alpha), anchor="mm")

    def full_tint(self, color, alpha):
        if not PIL_OK:
            return
        self.d.rectangle([0, 0, self.w, self.h], fill=(*color, int(alpha)))

    # ── Salida ──
    def result(self):
        if not PIL_OK:
            return self.frame
        out = Image.alpha_composite(self.base, self.layer).convert("RGB")
        return cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)
