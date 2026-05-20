# main.py — Punto de entrada de WakeUP (Fase 1: EAR)
#
# Este archivo orquesta todos los módulos.
# El loop principal es:
#   1. Capturar frame
#   2. Detectar rostro y ojos
#   3. Calcular EAR
#   4. Si EAR < umbral por N frames → ALERTA
#   5. Dibujar info en pantalla
#   6. Repetir
#
# Controles:
#   Q o ESC → Salir
#   C       → Entrar a modo calibración (muestra EAR en tiempo real)

import sys
import time
import cv2
import numpy as np

import config
from capture.camera import Camera
from detection.face_detector import FaceDetector
from detection.ear_calculator import compute_avg_ear
from alerts.alert_system import AlertSystem


def draw_hud(frame, ear, counter, fps, alert_system):
    """Dibuja el HUD (heads-up display) sobre el frame."""
    h, w = frame.shape[:2]

    # Barra de estado superior
    cv2.rectangle(frame, (0, 0), (w, 45), (30, 30, 30), -1)

    # EAR
    if config.SHOW_EAR_VALUE:
        color = (0, 255, 0) if ear > config.EAR_THRESHOLD else (0, 0, 255)
        cv2.putText(frame, f"EAR: {ear:.3f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Contador de frames con ojos cerrados
    cv2.putText(frame, f"Cerrado: {counter}/{config.EAR_CONSEC_FRAMES}",
                (200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    # FPS
    if config.SHOW_FPS:
        cv2.putText(frame, f"FPS: {fps:.0f}", (w - 110, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    # Estado
    if counter >= config.EAR_CONSEC_FRAMES:
        status = "SOMNOLIENTO"
        status_color = (0, 0, 255)
    elif ear < config.EAR_THRESHOLD:
        status = "OJOS CERRADOS"
        status_color = (0, 165, 255)
    else:
        status = "ALERTA"
        status_color = (0, 255, 0)

    cv2.putText(frame, status, (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

    # Barra visual de EAR (como un medidor)
    bar_w = int(np.clip(ear / 0.4, 0, 1) * 200)
    cv2.rectangle(frame, (w - 220, h - 30), (w - 220 + bar_w, h - 10),
                  (0, int(255 * min(ear / 0.3, 1)), 0), -1)
    cv2.rectangle(frame, (w - 220, h - 30), (w - 20, h - 10),
                  (100, 100, 100), 1)

    # Línea del umbral en la barra
    thresh_x = w - 220 + int((config.EAR_THRESHOLD / 0.4) * 200)
    cv2.line(frame, (thresh_x, h - 32), (thresh_x, h - 8), (0, 0, 255), 2)

    return frame


def main():
    print("=" * 50)
    print("  WakeUP — Sistema de Detección de Microsueños")
    print("  Fase 1: Eye Aspect Ratio (EAR)")
    print("=" * 50)
    print()
    print(f"  Umbral EAR:     {config.EAR_THRESHOLD}")
    print(f"  Frames alerta:  {config.EAR_CONSEC_FRAMES}")
    print(f"  Cooldown:       {config.ALERT_COOLDOWN}s")
    print()
    print("  Controles: Q/ESC=Salir | C=Calibrar")
    print("=" * 50)

    # Inicializar módulos
    camera = Camera()
    detector = FaceDetector()
    alert = AlertSystem()

    # Estado
    closed_counter = 0   # Frames consecutivos con ojos cerrados
    ear = 0.0
    fps = 0.0
    prev_time = time.time()

    try:
        while True:
            # 1. Capturar
            success, frame = camera.read()
            if not success:
                print("[Main] No se pudo leer frame, reintentando...")
                continue

            # Espejo (más natural para el usuario)
            frame = cv2.flip(frame, 1)

            # 2. Detectar rostro
            landmarks, results = detector.process(frame)

            if landmarks is not None:
                # 3. Extraer puntos de los ojos
                left_eye = detector.get_left_eye(landmarks)
                right_eye = detector.get_right_eye(landmarks)

                # 4. Calcular EAR
                ear, left_ear, right_ear = compute_avg_ear(left_eye, right_eye)

                # 5. Lógica de detección
                if ear < config.EAR_THRESHOLD:
                    closed_counter += 1
                    if closed_counter >= config.EAR_CONSEC_FRAMES:
                        alert.trigger()
                else:
                    closed_counter = 0
                    alert.reset()

                # 6. Dibujar ojos
                if config.SHOW_LANDMARKS:
                    detector.draw_eyes(frame, landmarks)

            else:
                # No se detectó rostro
                cv2.putText(frame, "Sin rostro detectado", (10, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Calcular FPS
            current_time = time.time()
            fps = 1.0 / (current_time - prev_time + 1e-6)
            prev_time = current_time

            # Dibujar HUD y alerta
            frame = draw_hud(frame, ear, closed_counter, fps, alert)
            frame = alert.draw_alert(frame)

            # Mostrar
            cv2.imshow("WakeUP", frame)

            # Controles
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):  # Q o ESC
                break
            elif key == ord('c'):
                print(f"[Calibración] EAR actual: {ear:.4f} | "
                      f"Izq: {left_ear:.4f} | Der: {right_ear:.4f}")

    except KeyboardInterrupt:
        print("\n[Main] Interrumpido por el usuario")
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print("[Main] WakeUP cerrado")


if __name__ == "__main__":
    main()
