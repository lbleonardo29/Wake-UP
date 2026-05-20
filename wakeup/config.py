# config.py — Configuración centralizada de WakeUP
# Todo lo que puedas querer ajustar está aquí, no disperso en 10 archivos.

# ── Cámara ──
CAMERA_INDEX = 0          # 0 = webcam principal, 1 = segunda cámara
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# ── Detección de ojos (EAR) ──
EAR_THRESHOLD = 0.22      # Debajo de este valor, el ojo se considera cerrado
                          # Calibra esto con tu cara: corre calibrate.py
EAR_CONSEC_FRAMES = 15    # Frames consecutivos con EAR bajo para activar alerta
                          # A 30 FPS, 15 frames ≈ 0.5 segundos

# ── Alerta ──
ALERT_SOUND = "alerts/beep.wav"  # Ruta al sonido de alerta (se genera automáticamente)
ALERT_COOLDOWN = 3.0      # Segundos mínimos entre alertas (evita spam)

# ── Visualización ──
SHOW_LANDMARKS = True      # Mostrar puntos de MediaPipe en pantalla
SHOW_EAR_VALUE = True      # Mostrar el valor del EAR en pantalla
SHOW_FPS = True            # Mostrar frames por segundo
