# alerts/alert_system.py — Sistema de alertas
#
# Visual : tinte rojo pulsante sobre el frame + texto "¡DESPIERTA!"
# Sonora : beep doble no bloqueante
#
# Audio en cascada:
#   1. pygame.mixer  → cross-platform, no bloqueante
#   2. winsound      → siempre disponible en Windows, corre en hilo
#   Si ninguno funciona, sólo alerta visual.
#
# Path del WAV: absoluto (basado en la ubicación de este archivo) para no
# depender del directorio de trabajo desde donde se invoque main.py.

import os
import sys
import math
import time
import struct
import wave

import config
from utils import ui

# ── Ruta absoluta al WAV ────────────────────────────────────────────────────
_ALERTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SOUND_FILE = os.path.join(_ALERTS_DIR, "alert.wav")


def _generate_beep(path):
    """Genera un WAV con beep doble a 950 Hz (urgente pero no molesto)."""
    sample_rate = 44100
    beep_dur = 0.14
    gap_dur = 0.07
    freq = 950

    def tone(n):
        for i in range(n):
            t = i / sample_rate
            env = min(t / 0.01, 1.0) * min((beep_dur - t) / 0.01, 1.0)
            yield int(32767 * env * math.sin(2 * math.pi * freq * t))

    n_beep = int(sample_rate * beep_dur)
    n_gap = int(sample_rate * gap_dur)

    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for _ in range(2):
            for v in tone(n_beep):
                wf.writeframes(struct.pack("<h", v))
            wf.writeframes(b"\x00\x00" * n_gap)


if not os.path.exists(_SOUND_FILE):
    try:
        _generate_beep(_SOUND_FILE)
        print(f"[AlertSystem] Sonido generado: {_SOUND_FILE}")
    except Exception as e:
        print(f"[AlertSystem] No se pudo generar el sonido: {e}")

# ── Backend de audio ────────────────────────────────────────────────────────
_pygame_sound = None
try:
    import pygame
    pygame.mixer.init()
    _pygame_sound = pygame.mixer.Sound(_SOUND_FILE)
    print("[AlertSystem] Backend: pygame")
except Exception:
    pass  # intentaremos winsound

_winsound = None
if sys.platform == "win32":
    try:
        import winsound as _winsound
        if _pygame_sound is None:
            print("[AlertSystem] Backend: winsound (PlaySound async)")
    except ImportError:
        pass

if _pygame_sound is None and _winsound is None:
    print("[AlertSystem] Sin backend de audio — solo alerta visual")


# ── Clase principal ─────────────────────────────────────────────────────────

class AlertSystem:
    def __init__(self):
        self.last_alert_time = 0
        self.alert_active = False

    def _play_sound(self):
        """Reproduce el beep sin bloquear el loop de video."""
        if _pygame_sound is not None:
            try:
                _pygame_sound.play()
                return
            except Exception:
                pass
        if _winsound is not None:
            # SND_FILENAME | SND_ASYNC reproduce el WAV sin bloquear el loop
            _winsound.PlaySound(
                _SOUND_FILE,
                _winsound.SND_FILENAME | _winsound.SND_ASYNC | _winsound.SND_NODEFAULT,
            )

    def trigger(self):
        """Dispara la alerta (con cooldown para no repetir cada frame)."""
        now = time.time()
        if now - self.last_alert_time < config.ALERT_COOLDOWN:
            return
        self.alert_active = True
        self.last_alert_time = now
        self._play_sound()

    def reset(self):
        """Desactiva la alerta cuando el conductor vuelve a estar despierto."""
        self.alert_active = False

    def draw_alert(self, ov):
        """Tinte rojo pulsante + texto sobre el overlay."""
        if not self.alert_active:
            return ov
        pulse = 0.5 + 0.5 * math.sin(time.time() * 6.0)
        ov.full_tint(ui.COL_DANGER, alpha=70 + 50 * pulse)
        cx, cy = ov.w // 2, ov.h // 2
        ov.text_centered(cx, cy - 18, "¡DESPIERTA!", size=78, bold=True,
                         color=(255, 255, 255))
        ov.text_centered(cx, cy + 48, "Mantente alerta", size=28, bold=False,
                         color=(255, 230, 230))
        return ov
