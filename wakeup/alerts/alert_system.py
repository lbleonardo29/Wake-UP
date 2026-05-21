# alerts/alert_system.py — Sistema de alertas
#
# Dos tipos de alerta:
# 1. Visual: el frame se tiñe de rojo (pulsante) + texto "¡DESPIERTA!"
# 2. Sonora: un beep doble no bloqueante para despertar al conductor
#
# Audio: usamos pygame.mixer (no bloqueante, cross-platform). Si no está
# disponible, caemos a winsound en un hilo (Windows) para no congelar el video.

import time
import math
import threading
import config
from utils import ui

# pygame es opcional — si no lo tiene, intentamos winsound (Windows)
try:
    import pygame
    pygame.mixer.init()
    SOUND_BACKEND = "pygame"
except Exception:
    try:
        import winsound  # solo Windows
        SOUND_BACKEND = "winsound"
    except ImportError:
        SOUND_BACKEND = None
        print("[AlertSystem] Sin backend de audio, solo alertas visuales")


class AlertSystem:
    def __init__(self):
        self.last_alert_time = 0
        self.alert_active = False

        # Generar beep si no existe (solo lo necesita pygame)
        if SOUND_BACKEND == "pygame":
            self._ensure_sound()
            try:
                self._sound = pygame.mixer.Sound(config.ALERT_SOUND)
            except Exception as e:
                print(f"[AlertSystem] No se pudo cargar el sonido: {e}")
                self._sound = None

    def _ensure_sound(self):
        """Genera el WAV de alerta si no existe."""
        import os
        sound_path = config.ALERT_SOUND
        os.makedirs(os.path.dirname(sound_path), exist_ok=True)

        if not os.path.exists(sound_path):
            self._generate_beep(sound_path)
            print(f"[AlertSystem] Sonido generado en {sound_path}")

    def _generate_beep(self, path):
        """Crea un WAV con un beep doble (más perceptible para despertar)."""
        import struct
        import wave

        sample_rate = 44100
        beep = 0.14            # duración de cada beep
        gap = 0.07             # silencio entre beeps
        frequency = 950        # tono agudo, urgente pero no molesto

        def tone(samples):
            for i in range(samples):
                t = i / sample_rate
                env = min(t / 0.01, 1.0) * min((beep - t) / 0.01, 1.0)
                yield int(32767 * env * math.sin(2 * math.pi * frequency * t))

        n_beep = int(sample_rate * beep)
        n_gap = int(sample_rate * gap)

        with wave.open(path, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            for _ in range(2):  # dos beeps
                for v in tone(n_beep):
                    wav.writeframes(struct.pack('<h', v))
                for _ in range(n_gap):
                    wav.writeframes(struct.pack('<h', 0))

    def _play_sound(self):
        """Reproduce el sonido de forma no bloqueante."""
        if SOUND_BACKEND == "pygame":
            if self._sound is not None:
                try:
                    self._sound.play()
                except Exception as e:
                    print(f"[AlertSystem] Error de audio: {e}")
        elif SOUND_BACKEND == "winsound":
            def _beep():
                try:
                    winsound.Beep(950, 140)
                    winsound.Beep(950, 140)
                except Exception:
                    pass
            threading.Thread(target=_beep, daemon=True).start()

    def trigger(self):
        """Dispara la alerta si pasó el cooldown."""
        now = time.time()
        if now - self.last_alert_time < config.ALERT_COOLDOWN:
            return  # Aún en cooldown

        self.alert_active = True
        self.last_alert_time = now
        self._play_sound()

    def reset(self):
        """Resetea la alerta cuando el conductor vuelve a estar alerta."""
        self.alert_active = False

    def draw_alert(self, ov):
        """Dibuja tinte rojo pulsante + texto de alerta sobre el overlay."""
        if not self.alert_active:
            return ov

        # Tinte rojo pulsante (atrae la mirada)
        pulse = 0.5 + 0.5 * math.sin(time.time() * 6.0)
        ov.full_tint(ui.COL_DANGER, alpha=70 + 50 * pulse)

        cx, cy = ov.w // 2, ov.h // 2
        ov.text_centered(cx, cy - 18, "¡DESPIERTA!", size=78, bold=True,
                         color=(255, 255, 255))
        ov.text_centered(cx, cy + 48, "Mantente alerta", size=28, bold=False,
                         color=(255, 230, 230))
        return ov
