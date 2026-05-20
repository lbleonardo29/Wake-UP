# Wake-UP — Sistema de Detección de Somnolencia y Microsueños (Fase 1: EAR)

Este es el proyecto final para la materia **Teorías de Procesamiento de Imágenes**. **Wake-UP** es un sistema inteligente que procesa video en tiempo real desde una cámara web para monitorear la fatiga del operador y prevenir accidentes ocasionados por microsueños.

El núcleo matemático y conceptual de esta primera fase es el cálculo del **Eye Aspect Ratio (EAR)** de forma robusta e invariante a la distancia de la persona respecto a la cámara.

---

## 👁️ Fundamentos Teóricos: ¿Cómo funciona el EAR?

El **Eye Aspect Ratio (EAR)** es una relación geométrica basada en puntos de referencia faciales (landmarks) distribuidos alrededor de los ojos. 

Para cada ojo, MediaPipe detecta **6 puntos críticos**:

```text
       P2    P3
   P1            P4   <-- (Esquina exterior a esquina interior)
       P6    P5
```

### La Ecuación EAR

$$EAR = \frac{\|P_2 - P_6\| + \|P_3 - P_5\|}{2 \cdot \|P_1 - P_4\|}$$

Donde:
* **$\|P_2 - P_6\|$ y $\|P_3 - P_5\|$** miden la apertura o distancia vertical del párpado.
* **$\|P_1 - P_4\|$** mide el ancho o distancia horizontal del ojo.
* El factor **$2$** en el denominador equilibra la escala de ambas proporciones.

### ¿Por qué EAR en lugar de umbrales de píxeles?
1. **Invarianza a la escala:** El valor de EAR es una relación proporcional. Esto significa que si la persona se acerca o se aleja de la cámara, la relación se mantiene estable.
2. **Robustez lumínica:** A diferencia de algoritmos basados en detección de pupilas por color o umbrales binarios de brillo, los puntos clave se calculan mediante redes neuronales convolucionales adaptables a cambios de luz.
3. **Valores Típicos:**
   * **Ojos Abiertos:** El EAR suele oscilar entre `0.25` y `0.35`.
   * **Ojos Cerrados:** El EAR cae drásticamente a un rango de `0.05` a `0.15`.

---

## 🛠️ Características Principales

* **Detección Avanzada con MediaPipe Tasks API:** Implementación moderna que utiliza el modelo `face_landmarker.task` de MediaPipe para obtener 478 landmarks faciales tridimensionales de manera ultra-rápida.
* **Cálculo de EAR Promedio:** Promedia el EAR de ambos ojos para evitar falsos positivos producidos por parpadeos asimétricos o sombreado parcial en un lado del rostro.
* **Filtrado Temporal de Microsueños:** Alerta visual y sonora solo cuando el EAR desciende del umbral por un mínimo de **$N$ frames consecutivos** (evitando alertar por parpadeos naturales de una fracción de segundo).
* **Alerta Multi-Sensorial:**
  * **Visual:** Overlay rojo semitransparente sobre la pantalla con el aviso de alta visibilidad `¡DESPIERTA!`.
  * **Sonora (No bloqueante):** Señal de audio (`beep.wav`) generada a través de `pygame.mixer` que se ejecuta en segundo plano para no congelar ni retrasar el flujo de video.
* **HUD (Heads-Up Display) Interactivo:**
  * Indicador numérico de EAR y contador de frames acumulados.
  * Gráfico de barra horizontal dinámico que funciona como medidor de cansancio en tiempo real, mostrando visualmente la cercanía al límite de alerta.
  * Contador en tiempo real de FPS (Frames por Segundo).
* **Modo de Calibración Integrado:** Script dedicado e interactivo (`calibrate.py`) que recolecta estadísticas de tus ojos abiertos y cerrados para calcular tu umbral óptimo personalizado.

---

## 📁 Estructura del Proyecto

El repositorio está organizado en módulos independientes con responsabilidades bien delimitadas:

```text
wakeup_fase1/
├── .gitignore               # Archivos excluidos del control de versiones (caché, entornos, etc.)
├── README.md                # Documentación del proyecto (esta guía)
└── wakeup/
    ├── main.py              # Archivo de entrada principal que orquesta el sistema completo
    ├── config.py            # Configuración centralizada de variables, límites y umbrales
    ├── calibrate.py         # Script interactivo para calibrar el umbral EAR personalizado
    ├── requirements.txt     # Lista de dependencias de Python necesarias
    ├── alerts/
    │   ├── __init__.py
    │   ├── alert_system.py  # Manejo de alertas visuales (OpenCV) y sonoras (Pygame)
    │   └── beep.wav         # Archivo de sonido para alertas (generado automáticamente)
    ├── capture/
    │   ├── __init__.py
    │   └── camera.py        # Wrapper para inicialización segura de la webcam con OpenCV
    ├── detection/
    │   ├── __init__.py
    │   ├── face_detector.py # Detector facial y mapeo de landmarks con MediaPipe Tasks
    │   ├── ear_calculator.py# Implementación matemática de la fórmula EAR
    │   └── face_landmarker.task # Archivo binario de la red neuronal (descarga automática)
    ├── model/
    │   └── __init__.py      # Reservado para futuros modelos convolucionales de la fase 2
    └── utils/
        └── __init__.py      # Funciones utilitarias generales
```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar o Instalar Dependencias
Asegúrate de estar en el directorio `wakeup_fase1/wakeup` e instala las librerías necesarias con `pip`:

```bash
pip install -r requirements.txt
```

> 💡 **Nota sobre MediaPipe:** La primera vez que inicies el sistema, el detector facial detectará que no cuentas con el archivo de red neuronal y lo **descargará automáticamente** (~5MB) sin necesidad de descargas manuales.

---

## 📈 Instrucciones de Uso

### Calibración del Umbral (Recomendado)
Dado que cada persona tiene una fisonomía ocular distinta (algunas personas tienen ojos más achinados o abiertos que otras), te recomendamos **calibrar el sistema**:

1. Ejecuta el script de calibración:
   ```bash
   python calibrate.py
   ```
2. Sigue las instrucciones interactivas en la consola:
   * Te pedirá mirar a la cámara fijamente con los **ojos bien abiertos** por 3 segundos.
   * Te pedirá mirar a la cámara con los **ojos totalmente cerrados** por otros 3 segundos.
3. Al finalizar, la consola mostrará tus métricas y te indicará el **Umbral Recomendado**.
4. Abre `config.py` y edita la variable `EAR_THRESHOLD` con este valor sugerido.

### Ejecución Principal
Una vez configurado o con los valores por defecto, inicia el programa principal:

```bash
python main.py
```

### Controles en Pantalla
Cuando la ventana de visualización esté activa, puedes interactuar mediante las siguientes teclas:
* `C` (en la terminal): Imprime en tiempo real los valores exactos de EAR actuales del ojo izquierdo, derecho y promedio.
* `Q` o `ESC`: Cierra de forma segura la ventana del programa, apaga la webcam y detiene los hilos de audio.

---

## ⚙️ Parámetros de Ajuste (`config.py`)

Puedes abrir y personalizar el comportamiento del sistema desde [config.py](file:///c:/Proyectos_TPIM/Proyecto_final/wakeup_fase1/wakeup/config.py):

* `CAMERA_INDEX`: Índice de cámara web a usar (por defecto `0` para cámaras internas/webcams).
* `EAR_THRESHOLD`: El límite inferior de EAR. Si tu EAR promedio cae por debajo de este número, tus ojos se considerarán cerrados (ej. `0.22`).
* `EAR_CONSEC_FRAMES`: La cantidad de frames continuos que deben estar cerrados para que se considere un microsueño e inicie la alarma. A 30 FPS, un valor de `15` equivale a aproximadamente `0.5` segundos.
* `ALERT_COOLDOWN`: El enfriamiento (cooldown) en segundos para evitar que la alarma suene repetidamente de forma molesta.
* `SHOW_LANDMARKS`: Muestra en color verde el delineado de los ojos sobre tu rostro.
* `SHOW_EAR_VALUE`: Muestra el valor EAR actual de forma numérica sobre el HUD.
