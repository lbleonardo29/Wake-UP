# capture/camera.py — Wrapper de VideoCapture

import cv2
import config


class Camera:
    def __init__(self):
        # En Windows, DSHOW es más estable que el backend por defecto
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"No se pudo abrir la cámara {config.CAMERA_INDEX}. "
                "Verifica que esté conectada."
            )

        # Configurar resolución DESPUÉS de abrir (y sin forzar si falla)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[Camera] Iniciada ({w}x{h}) con backend DSHOW")

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return False, None
        return True, frame

    def release(self):
        self.cap.release()
        print("[Camera] Liberada")