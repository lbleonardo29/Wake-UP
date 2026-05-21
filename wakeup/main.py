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
from utils import ui


def draw_hud(ov, ear, counter, fps, face_ok):
    """Dibuja el HUD (heads-up display) sobre el overlay."""
    w, h = ov.w, ov.h

    # ── Estado actual ──
    if counter >= config.EAR_CONSEC_FRAMES:
        status, status_color = "SOMNOLIENTO", ui.COL_DANGER
    elif ear < config.EAR_THRESHOLD:
        status, status_color = "OJOS CERRADOS", ui.COL_WARN
    else:
        status, status_color = "ALERTA", ui.COL_OK
    ear_color = ui.COL_OK if ear > config.EAR_THRESHOLD else ui.COL_DANGER

    # ── Barra superior ──
    ov.panel((0, 0, w, 72), color=ui.COL_PANEL, alpha=205, radius=0)
    ov.text((28, 36), "Wake", size=30, bold=True, color=ui.COL_TEXT, anchor="lm")
    ear_lbl_w = 96  # ancho aproximado de "Wake"
    ov.text((28 + ear_lbl_w, 36), "UP", size=30, bold=True,
            color=ui.COL_ACCENT, anchor="lm")

    # EAR
    if config.SHOW_EAR_VALUE:
        ov.text((300, 22), "EAR", size=15, color=ui.COL_DIM, anchor="lm")
        ov.text((300, 46), f"{ear:.3f}", size=26, bold=True,
                color=ear_color, anchor="lm")

    # Contador de cierre
    ov.text((430, 22), "CIERRE", size=15, color=ui.COL_DIM, anchor="lm")
    ov.text((430, 46), f"{counter}/{config.EAR_CONSEC_FRAMES}", size=26,
            bold=True, color=ui.COL_TEXT, anchor="lm")

    # FPS
    if config.SHOW_FPS:
        ov.text((w - 28, 22), "FPS", size=15, color=ui.COL_DIM, anchor="rm")
        ov.text((w - 28, 46), f"{fps:.0f}", size=26, bold=True,
                color=ui.COL_TEXT, anchor="rm")

    # ── Badge de estado (abajo izquierda) ──
    if face_ok:
        bw, bh = 260, 56
        bx, by = 28, h - bh - 28
        ov.panel((bx, by, bx + bw, by + bh), color=status_color, alpha=46,
                 radius=14)
        ov.bar((bx, by + 14, bx + 8, by + bh - 14), status_color, radius=4)
        ov.text((bx + 24, by + bh // 2), status, size=24, bold=True,
                color=status_color, anchor="lm")

    # ── Medidor EAR (abajo derecha) ──
    mw = 300
    mx, my = w - mw - 28, h - 40
    ov.text((mx, my - 22), "Nivel de apertura", size=14, color=ui.COL_DIM,
            anchor="lm")
    ov.panel((mx, my, mx + mw, my + 18), color=(40, 44, 56), alpha=220,
             radius=9)
    fill_w = int(np.clip(ear / 0.4, 0, 1) * mw)
    if fill_w > 6:
        ov.bar((mx, my, mx + fill_w, my + 18), ear_color, radius=9)
    # Marca del umbral
    thresh_x = mx + int((config.EAR_THRESHOLD / 0.4) * mw)
    ov.line((thresh_x, my - 4), (thresh_x, my + 22), ui.COL_DANGER, width=2)

    return ov


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

    # Ventana redimensionable, iniciada al tamaño de captura
    cv2.namedWindow("WakeUP", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("WakeUP", config.FRAME_WIDTH, config.FRAME_HEIGHT)

    # Estado
    closed_counter = 0   # Frames consecutivos con ojos cerrados
    ear = 0.0
    left_ear = right_ear = 0.0
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
            face_ok = landmarks is not None

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

            # Calcular FPS
            current_time = time.time()
            fps = 1.0 / (current_time - prev_time + 1e-6)
            prev_time = current_time

            # Dibujar HUD y alerta sobre un overlay con fuentes TrueType
            ov = ui.Overlay(frame)
            draw_hud(ov, ear, closed_counter, fps, face_ok)
            if not face_ok:
                ov.text_centered(ov.w // 2, 110, "Sin rostro detectado",
                                 size=26, bold=True, color=ui.COL_DIM)
            alert.draw_alert(ov)

            # Mostrar
            cv2.imshow("WakeUP", ov.result())

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
