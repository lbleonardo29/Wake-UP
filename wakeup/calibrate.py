# calibrate.py — Script de calibración de umbral EAR
#
# ¿Por qué calibrar?
# Cada persona tiene ojos diferentes. El EAR con ojos abiertos puede ser
# 0.30 para alguien y 0.22 para otro. Sin calibrar, el sistema puede dar
# falsas alarmas o no detectar nada.
#
# Cómo usarlo:
#   1. Corre: python calibrate.py
#   2. Mira a la cámara con ojos bien abiertos por 3 segundos
#   3. Cierra los ojos por 3 segundos
#   4. El script te dice qué umbral poner en config.py

import time
import cv2
import numpy as np

import config
from capture.camera import Camera
from detection.face_detector import FaceDetector
from detection.ear_calculator import compute_avg_ear


def calibrate():
    print("=" * 50)
    print("  WakeUP — Calibración de Umbral EAR")
    print("=" * 50)

    camera = Camera()
    detector = FaceDetector()

    # Fase 1: Ojos abiertos
    print("\n>>> FASE 1: Mira a la cámara con los ojos bien ABIERTOS")
    print("    Tienes 3 segundos...")
    input("    Presiona ENTER cuando estés listo...")

    open_ears = _collect_ears(camera, detector, duration=3.0, label="ABIERTOS")

    # Fase 2: Ojos cerrados
    print("\n>>> FASE 2: Ahora CIERRA los ojos")
    print("    Tienes 3 segundos...")
    input("    Presiona ENTER cuando estés listo...")

    closed_ears = _collect_ears(camera, detector, duration=3.0, label="CERRADOS")

    camera.release()
    cv2.destroyAllWindows()

    # Calcular umbral
    if not open_ears or not closed_ears:
        print("\n[Error] No se pudieron capturar suficientes datos.")
        print("Verifica que la cámara detecte tu rostro.")
        return

    avg_open = np.mean(open_ears)
    avg_closed = np.mean(closed_ears)
    std_open = np.std(open_ears)

    # El umbral ideal está entre el promedio de cerrado y abierto
    # Usamos un punto al 40% entre ambos (más cerca del cerrado)
    threshold = avg_closed + 0.4 * (avg_open - avg_closed)

    print("\n" + "=" * 50)
    print("  RESULTADOS DE CALIBRACIÓN")
    print("=" * 50)
    print(f"  EAR promedio (ojos abiertos):  {avg_open:.4f}")
    print(f"  EAR promedio (ojos cerrados):  {avg_closed:.4f}")
    print(f"  Desviación (abiertos):         {std_open:.4f}")
    print(f"")
    print(f"  >>> UMBRAL RECOMENDADO: {threshold:.3f}")
    print(f"")
    print(f"  Actualiza en config.py:")
    print(f"  EAR_THRESHOLD = {threshold:.3f}")
    print("=" * 50)


def _collect_ears(camera, detector, duration, label):
    """Recolecta valores EAR durante un período."""
    ears = []
    start = time.time()

    while time.time() - start < duration:
        success, frame = camera.read()
        if not success:
            continue

        frame = cv2.flip(frame, 1)
        landmarks, _ = detector.process(frame)

        if landmarks is not None:
            left = detector.get_left_eye(landmarks)
            right = detector.get_right_eye(landmarks)
            ear, _, _ = compute_avg_ear(left, right)
            ears.append(ear)

            # Mostrar en pantalla
            color = (0, 255, 0) if label == "ABIERTOS" else (0, 0, 255)
            cv2.putText(frame, f"EAR: {ear:.4f} ({label})", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            elapsed = time.time() - start
            cv2.putText(frame, f"Tiempo: {elapsed:.1f}/{duration:.1f}s",
                        (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (200, 200, 200), 1)

        cv2.imshow("WakeUP - Calibracion", frame)
        cv2.waitKey(1)

    print(f"    Capturados {len(ears)} valores EAR ({label})")
    return ears


if __name__ == "__main__":
    calibrate()
