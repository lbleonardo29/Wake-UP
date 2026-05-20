# alerts/alert_system.py — Sistema de alertas
#
# Dos tipos de alerta:
# 1. Visual: el frame se pinta de rojo + texto "¡DESPIERTA!"
# 2. Sonora: un beep usando pygame (no bloqueante)
#
# ¿Por qué pygame para audio y no playsound o winsound?
# - playsound es bloqueante (congela el video mientras suena)
# - winsound solo funciona en Windows
# - pygame.mixer es no bloqueante, cross-platform y ligero

import time
import cv2
import numpy as np
import config

# pygame es opcional — si no lo tiene, solo alerta visual
try:
    import pygame
    pygame.mixer.init()
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    print("[AlertSystem] pygame no instalado, solo alertas visuales")


class AlertSystem:
    def __init__(self):
        self.last_alert_time = 0
        self.alert_active = False

        # Generar beep si no existe
        if SOUND_AVAILABLE:
            self._ensure_sound()

    def _ensure_sound(self):
        """Genera un archivo beep.wav si no existe."""
        import os
        sound_path = config.ALERT_SOUND
        os.makedirs(os.path.dirname(sound_path), exist_ok=True)

        if not os.path.exists(sound_path):
            self._generate_beep(sound_path)
            print(f"[AlertSystem] Beep generado en {sound_path}")

    def _generate_beep(self, path):
        """Crea un archivo WAV con un tono de alerta."""
        import struct
        import wave

        sample_rate = 44100
        duration = 0.5         # 0.5 segundos
        frequency = 880        # La4 alta (urgente pero no molesta)
        n_samples = int(sample_rate * duration)

        with wave.open(path, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)

            for i in range(n_samples):
                t = i / sample_rate
                # Tono con fade in/out para que no trone
                envelope = min(t / 0.05, 1.0) * min((duration - t) / 0.05, 1.0)
                value = int(32767 * envelope * np.sin(2 * np.pi * frequency * t))
                wav.writeframes(struct.pack('<h', value))

    def trigger(self):
        """Dispara la alerta si pasó el cooldown."""
        now = time.time()
        if now - self.last_alert_time < config.ALERT_COOLDOWN:
            return  # Aún en cooldown

        self.alert_active = True
        self.last_alert_time = now

        # Sonido
        if SOUND_AVAILABLE:
            try:
                sound = pygame.mixer.Sound(config.ALERT_SOUND)
                sound.play()
            except Exception as e:
                print(f"[AlertSystem] Error de audio: {e}")

    def reset(self):
        """Resetea la alerta cuando el conductor vuelve a estar alerta."""
        self.alert_active = False

    def draw_alert(self, frame):
        """Dibuja overlay rojo + texto de alerta sobre el frame."""
        if not self.alert_active:
            return frame

        # Overlay rojo semi-transparente
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]),
                      (0, 0, 255), -1)
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)

        # Texto de alerta
        text = "DESPIERTA!"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 1.5
        thickness = 3
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
        cx = (frame.shape[1] - tw) // 2
        cy = (frame.shape[0] + th) // 2

        # Sombra + texto
        cv2.putText(frame, text, (cx + 2, cy + 2), font, scale,
                    (0, 0, 0), thickness + 2)
        cv2.putText(frame, text, (cx, cy), font, scale,
                    (0, 0, 255), thickness)

        return frame
