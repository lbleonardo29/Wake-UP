# detection/face_detector.py — Detección facial con MediaPipe Tasks API
#
# MediaPipe 0.10.35+ eliminó mp.solutions y usa mp.tasks en su lugar.
# La lógica es la misma, solo cambia cómo se inicializa.

import os
import urllib.request
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker,
    FaceLandmarkerOptions,
    RunningMode,
)


# URL del modelo (se descarga automáticamente la primera vez)
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")


class FaceDetector:
    """Detecta rostro y extrae landmarks oculares con MediaPipe Tasks."""

    # Índices de los landmarks de cada ojo (mismos que antes)
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]
    LEFT_EYE = [33, 160, 158, 133, 153, 144]

    def __init__(self):
        self._ensure_model()

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = FaceLandmarker.create_from_options(options)
        print("[FaceDetector] MediaPipe Face Landmarker inicializado")

    def _ensure_model(self):
        """Descarga el modelo si no existe."""
        if os.path.exists(MODEL_PATH):
            return
        print("[FaceDetector] Descargando modelo (primera vez, ~5MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("[FaceDetector] Modelo descargado")

    def process(self, frame):
        """
        Procesa un frame BGR de OpenCV.
        Retorna:
            landmarks: lista de (x, y) en píxeles si detectó cara, None si no.
            result: objeto de MediaPipe
        """
        # Convertir BGR → RGB y crear mp.Image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self.landmarker.detect(mp_image)

        if not result.face_landmarks:
            return None, result

        face = result.face_landmarks[0]
        h, w = frame.shape[:2]

        # Convertir landmarks normalizados a píxeles
        landmarks = []
        for lm in face:
            landmarks.append((int(lm.x * w), int(lm.y * h)))

        return landmarks, result

    def get_eye_points(self, landmarks, eye_indices):
        return [landmarks[i] for i in eye_indices]

    def get_left_eye(self, landmarks):
        return self.get_eye_points(landmarks, self.LEFT_EYE)

    def get_right_eye(self, landmarks):
        return self.get_eye_points(landmarks, self.RIGHT_EYE)

    def draw_eyes(self, frame, landmarks):
        for eye_indices in [self.LEFT_EYE, self.RIGHT_EYE]:
            pts = np.array([landmarks[i] for i in eye_indices], np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 0), 1)
        return frame