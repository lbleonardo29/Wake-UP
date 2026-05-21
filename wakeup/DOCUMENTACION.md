# WakeUP — Documentación Técnica
**Fase 1 | Sistema de Detección de Microsueños por EAR**

---

## 1. ¿Qué hace el programa?

WakeUP abre la cámara web, analiza el video en tiempo real cuadro por cuadro y decide si el usuario tiene los ojos cerrados demasiado tiempo. Si detecta somnolencia, muestra una alerta visual (pantalla roja pulsante con el texto "¡DESPIERTA!") y hace sonar un beep doble para despertar al conductor.

El programa corre a aproximadamente 25–30 frames por segundo. En cada frame hace cuatro cosas: capturar, detectar, calcular y dibujar.

---

## 2. Estructura de archivos

```
wakeup/
├── main.py                  ← Punto de entrada: orquesta todo el loop
├── config.py                ← Todos los parámetros ajustables
├── calibrate.py             ← Herramienta auxiliar de calibración
├── requirements.txt         ← Librerías necesarias
│
├── capture/
│   └── camera.py            ← Abre la cámara y entrega frames
│
├── detection/
│   ├── face_detector.py     ← Localiza el rostro y extrae 478 landmarks
│   ├── ear_calculator.py    ← Calcula el Eye Aspect Ratio (EAR)
│   └── face_landmarker.task ← Modelo de MediaPipe (se descarga solo)
│
├── alerts/
│   ├── alert_system.py      ← Dispara la alerta visual y sonora
│   └── alert.wav            ← Sonido generado automáticamente al iniciar
│
└── utils/
    └── ui.py                ← Motor de renderizado con fuentes TrueType
```

---

## 3. Flujo de ejecución

Cuando corrés `python main.py`, la secuencia es esta:

```
Arranque
   │
   ├─ Inicializar cámara     (capture/camera.py)
   ├─ Cargar modelo MediaPipe (detection/face_detector.py)
   ├─ Generar alert.wav      (alerts/alert_system.py)
   └─ Abrir ventana 1280×720
          │
          ▼
   ┌──────────────────────────────┐
   │  LOOP (por cada frame)       │
   │                              │
   │  1. Capturar frame           │
   │  2. Espejear (flip)          │
   │  3. Detectar rostro          │
   │  4. Calcular EAR             │
   │  5. Incrementar contador     │
   │     si EAR < umbral          │
   │  6. Disparar alerta si       │
   │     contador ≥ 15 frames     │
   │  7. Dibujar HUD sobre frame  │
   │  8. Mostrar en ventana       │
   │  9. Leer tecla (Q/ESC/C)     │
   └──────────────────────────────┘
          │
          ▼
   Liberar cámara y cerrar
```

El loop corre indefinidamente hasta que el usuario presiona **Q** o **ESC**.

---

## 4. Módulo por módulo

### 4.1 `config.py` — Configuración central

Todos los números importantes están aquí, en un único archivo. No hay que buscar por el código para ajustar un parámetro.

| Variable | Valor por defecto | Qué controla |
|---|---|---|
| `CAMERA_INDEX` | `0` | Qué cámara usar (0 = principal) |
| `FRAME_WIDTH` | `1280` | Ancho de captura en píxeles |
| `FRAME_HEIGHT` | `720` | Alto de captura en píxeles |
| `EAR_THRESHOLD` | `0.22` | Umbral: debajo = ojo cerrado |
| `EAR_CONSEC_FRAMES` | `15` | Frames consecutivos para activar alerta |
| `ALERT_COOLDOWN` | `3.0` | Segundos mínimos entre beeps |
| `SHOW_LANDMARKS` | `True` | Dibujar contorno de ojos sobre la imagen |
| `SHOW_EAR_VALUE` | `True` | Mostrar valor EAR en pantalla |
| `SHOW_FPS` | `True` | Mostrar frames por segundo |

---

### 4.2 `capture/camera.py` — Cámara

```python
camera = Camera()
success, frame = camera.read()
```

Abre la cámara usando el backend **DirectShow** de Windows (`cv2.CAP_DSHOW`), que es más estable que el backend genérico en ese sistema operativo. Configura la resolución a 1280×720 después de abrirla. Cada llamada a `read()` devuelve un frame como arreglo NumPy de forma `(720, 1280, 3)` — alto × ancho × canales BGR.

El frame se espeja horizontalmente en `main.py` (`cv2.flip(frame, 1)`) para que se comporte como un espejo: si movés la cabeza a la derecha, la imagen también va a la derecha.

---

### 4.3 `detection/face_detector.py` — Detector facial

Usa **MediaPipe Face Landmarker**, un modelo de Google que localiza **478 puntos de referencia** (landmarks) distribuidos por todo el rostro: frente, ojos, nariz, boca, mandíbula.

**Primera ejecución:** si el archivo `face_landmarker.task` no existe, lo descarga automáticamente desde los servidores de Google (~5 MB).

Los 478 landmarks vienen normalizados (valores entre 0.0 y 1.0). El detector los convierte a píxeles según el tamaño del frame.

Para los ojos se usan 6 landmarks específicos por cada ojo:

```
        P2    P3
    P1            P4      ← 6 puntos por ojo
        P6    P5

Ojo izquierdo (perspectiva cámara): índices 33, 160, 158, 133, 153, 144
Ojo derecho  (perspectiva cámara): índices 362, 385, 387, 263, 373, 380
```

El método `draw_eyes()` dibuja un polígono verde sobre cada ojo si `SHOW_LANDMARKS = True`.

---

### 4.4 `detection/ear_calculator.py` — El algoritmo EAR

**EAR = Eye Aspect Ratio** es la métrica central del proyecto. Fue propuesta por Soukupová y Čech en 2016 y es la forma más simple y robusta de detectar si un ojo está abierto o cerrado.

#### La fórmula

```
        |P2−P6| + |P3−P5|
EAR = ─────────────────────
           2 × |P1−P4|
```

- **Numerador:** suma de las dos distancias verticales (entre párpado superior e inferior).
- **Denominador:** el doble de la distancia horizontal (de esquina a esquina del ojo).

#### ¿Por qué funciona?

- Cuando el ojo está **abierto**: la apertura vertical es grande → EAR ≈ 0.25 a 0.35.
- Cuando el ojo está **cerrado**: los párpados se tocan → EAR ≈ 0.05 a 0.15.
- Es **invariante a la distancia**: si te alejás de la cámara, el numerador y el denominador escalan igual, y el ratio no cambia.

#### En el código

```python
ear, left_ear, right_ear = compute_avg_ear(left_eye, right_eye)
```

Se calcula el EAR de cada ojo por separado y se promedian. Esto compensa que un ojo puede parpadear ligeramente distinto al otro, o que la iluminación afecte más a un lado.

---

### 4.5 `alerts/alert_system.py` — Sistema de alertas

Tiene dos responsabilidades: decidir cuándo sonar/mostrar la alerta, y cómo hacerlo.

#### Lógica de disparo

```python
# En main.py, por cada frame:
if ear < EAR_THRESHOLD:
    closed_counter += 1
    if closed_counter >= EAR_CONSEC_FRAMES:   # 15 frames ≈ 0.5 s a 30 FPS
        alert.trigger()
else:
    closed_counter = 0
    alert.reset()
```

El contador se reinicia si el EAR vuelve a subir. Esto evita falsas alarmas por un parpadeo normal.

`trigger()` tiene un **cooldown de 3 segundos**: si ya sonó hace menos de 3 s, no vuelve a sonar aunque siga siendo llamado. Así el beep no se repite cada frame.

#### Sonido

El sonido se genera automáticamente al iniciar el programa (`alert.wav`, ~37 KB, beep doble a 950 Hz con fade-in/out para que no trone). Se intenta reproducir con dos backends en este orden:

1. **pygame.mixer** — cross-platform, no bloquea el video.
2. **winsound** — módulo nativo de Windows, corre en un hilo separado para no bloquear.

Al arrancar el programa se imprime en consola cuál backend se usó.

#### Alerta visual

Mientras `alert_active == True`, `draw_alert()` agrega sobre el frame:
- Un tinte rojo **pulsante** (la intensidad varía con una función seno a 6 Hz).
- El texto **"¡DESPIERTA!"** en grande, centrado, con sombra.
- El subtexto "Mantente alerta" debajo.

La alerta se desactiva en cuanto el EAR vuelve a superar el umbral.

---

### 4.6 `utils/ui.py` — Motor de renderizado

OpenCV solo tiene fuentes vectoriales simples (familia Hershey) que se ven bloquosas. Este módulo usa **Pillow (PIL)** para renderizar texto con fuentes TrueType del sistema operativo.

#### Cómo funciona

```python
ov = ui.Overlay(frame)   # convierte el frame BGR a imagen RGBA de Pillow
draw_hud(ov, ...)        # dibuja paneles y texto sobre una capa transparente
alert.draw_alert(ov)     # agrega el overlay de alerta si corresponde
frame = ov.result()      # compone la capa y convierte de vuelta a BGR
cv2.imshow("WakeUP", frame)
```

Toda la superposición se acumula en una sola capa RGBA y se compone una única vez al final, lo que es eficiente.

**Fuentes:** carga Segoe UI (Windows) con fallback a Arial y luego a DejaVu Sans. Si ninguna está disponible, usa la fuente por defecto de Pillow.

---

### 4.7 `main.py` — Orquestador

Es el punto de entrada. No contiene lógica de negocio — solo llama a los otros módulos en el orden correcto.

**`draw_hud(ov, ear, counter, fps, face_ok)`** dibuja todos los elementos del HUD sobre el overlay. Recibe el valor de EAR, el contador de frames con ojos cerrados, los FPS actuales y si se detectó un rostro.

---

## 5. La interfaz en pantalla

### Estado normal (rostro detectado, ojos abiertos)

```
┌────────────────────────────────────────────────────────┐
│ WakeUP    EAR        CIERRE                       FPS  │  ← Barra superior
│           0.310      3/15                          29  │
├────────────────────────────────────────────────────────┤
│                                                        │
│            [imagen de la cámara]                       │
│        ○ ──── contorno verde de ojos ────              │
│                                                        │
│                                                        │
│ ▌ ALERTA     ░░░░░░░░░░░░░░░░ Nivel de apertura ░░│   │  ← Barra inferior
└────────────────────────────────────────────────────────┘
```

#### Elementos del HUD

| Elemento | Posición | Qué muestra |
|---|---|---|
| **WakeUP** | Arriba izquierda | Nombre del sistema. "Wake" en blanco, "UP" en azul. |
| **EAR** | Arriba centro-izquierda | Valor numérico del Eye Aspect Ratio (3 decimales). Verde si > umbral, rojo si < umbral. |
| **CIERRE** | Arriba centro | Contador de frames consecutivos con ojos cerrados. Formato `actual/máximo` (ej: `3/15`). |
| **FPS** | Arriba derecha | Frames por segundo actuales. |
| **Badge de estado** | Abajo izquierda | Estado actual: **ALERTA** (verde), **OJOS CERRADOS** (ámbar) o **SOMNOLIENTO** (rojo). |
| **Medidor de apertura** | Abajo derecha | Barra horizontal que representa el EAR. La línea roja vertical es el umbral configurado. |
| **Contorno de ojos** | Sobre los ojos | Polígono verde que sigue los 6 landmarks de cada ojo (si `SHOW_LANDMARKS = True`). |

#### Colores del EAR y badge

| Situación | Color | EAR típico |
|---|---|---|
| Ojos abiertos, conductor despierto | Verde | > 0.22 |
| Ojos a medio cerrar / parpadeo largo | Ámbar | < 0.22 pero sin alarma aún |
| Ojos cerrados ≥ 15 frames (≈ 0.5 s) | Rojo | < 0.22 sostenido |

---

### Estado: sin rostro detectado

Si la cámara no ve ningún rostro (poca luz, cara fuera de encuadre, etc.), aparece el mensaje "Sin rostro detectado" en gris centrado en la parte superior. El badge de estado desaparece. El contador no incrementa.

---

### Estado: alerta activa

Cuando `closed_counter >= 15`:

- Toda la pantalla se tiñe de **rojo pulsante** (la intensidad varía con una onda sinusoidal a 6 Hz para que llame la atención).
- El texto **"¡DESPIERTA!"** aparece en grande, centrado, en blanco con sombra negra.
- Debajo: "Mantente alerta" en rosa claro.
- Simultáneamente suena el beep doble.
- La alerta desaparece cuando el EAR vuelve a superar el umbral (el conductor abre los ojos).

---

## 6. Salida en consola

Al arrancar, el programa imprime:

```
==================================================
  WakeUP — Sistema de Detección de Microsueños
  Fase 1: Eye Aspect Ratio (EAR)
==================================================

  Umbral EAR:     0.22
  Frames alerta:  15
  Cooldown:       3.0s

  Controles: Q/ESC=Salir | C=Calibrar
==================================================
[AlertSystem] Sonido generado: C:\...\alerts\alert.wav   ← solo primera vez
[AlertSystem] Backend: pygame                            ← o winsound
[Camera] Iniciada (1280x720) con backend DSHOW
[FaceDetector] MediaPipe Face Landmarker inicializado
```

Si durante la ejecución presionás **C**, imprime el EAR actual para calibración:

```
[Calibración] EAR actual: 0.3142 | Izq: 0.3088 | Der: 0.3196
```

Al cerrar:

```
[Camera] Liberada
[Main] WakeUP cerrado
```

---

## 7. Controles de teclado

| Tecla | Acción |
|---|---|
| **Q** o **ESC** | Cierra el programa |
| **C** | Imprime en consola el EAR actual de cada ojo (útil para calibrar el umbral) |

---

## 8. Calibración del umbral

El valor `EAR_THRESHOLD = 0.22` funciona bien para la mayoría de las personas, pero puede variar según la forma de los ojos y la distancia a la cámara. Para calibrar:

1. Corré el programa: `python main.py`
2. Mirá la cámara con los **ojos bien abiertos** y presioná **C** varias veces. Anotá los valores EAR (deberían estar entre 0.25 y 0.35).
3. Cerrá los ojos completamente y presioná **C**. Anotá los valores (deberían estar entre 0.05 y 0.15).
4. El umbral ideal está **a mitad de camino** entre ambos extremos, generalmente 0.20–0.24.
5. Editá `config.py` y cambiá `EAR_THRESHOLD` al valor que encontraste.

Alternativamente, podés correr `calibrate.py` directamente.

---

## 9. Dependencias

| Librería | Para qué se usa |
|---|---|
| `opencv-python` | Captura de cámara, visualización de la ventana, dibujo de landmarks |
| `mediapipe` | Detección facial y 478 landmarks con el modelo `face_landmarker.task` |
| `numpy` | Operaciones con arreglos (distancias euclidianas, composición de imágenes) |
| `pygame` | Reproducción de audio no bloqueante (fallback a winsound en Windows) |
| `Pillow` | Renderizado de texto con fuentes TrueType (Segoe UI) con antialiasing |

Instalación: `pip install -r requirements.txt`

---

## 10. Limitaciones de la Fase 1

- **Requiere buena iluminación frontal.** Si la cara está muy en sombra, MediaPipe no la detecta.
- **Un solo usuario.** El modelo solo analiza un rostro a la vez.
- **EAR no detecta microsueños con ojos entreabiertos.** Si alguien conduce adormecido pero con los ojos levemente abiertos, EAR puede estar sobre el umbral. Esto se aborda en fases futuras (análisis de textura del iris, parpadeo lento, etc.).
- **No hay persistencia.** Al cerrar el programa, la sesión se pierde. No guarda logs ni historial.
