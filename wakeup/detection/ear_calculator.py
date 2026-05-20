# detection/ear_calculator.py — Eye Aspect Ratio (EAR)
#
# EAR es la métrica que determina si un ojo está abierto o cerrado.
#
# Cómo funciona:
# Un ojo tiene 6 puntos de referencia:
#
#       P2    P3
#   P1            P4
#       P6    P5
#
# EAR = (|P2-P6| + |P3-P5|) / (2 * |P1-P4|)
#
# - Ojo abierto: EAR ≈ 0.25 - 0.35 (vertical > 0)
# - Ojo cerrado: EAR ≈ 0.05 - 0.15 (vertical → 0)
#
# ¿Por qué EAR y no simplemente contar píxeles negros?
# Porque EAR es invariante al tamaño de la imagen y la distancia
# a la cámara. No importa si estás a 30cm o 60cm, el ratio se mantiene.

import numpy as np


def distance(p1, p2):
    """Distancia euclidiana entre dos puntos (x, y)."""
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def compute_ear(eye_points):
    """
    Calcula el Eye Aspect Ratio para un ojo.

    Args:
        eye_points: lista de 6 tuplas (x, y) en este orden:
            [P1, P2, P3, P4, P5, P6]
            P1 = esquina exterior, P4 = esquina interior
            P2, P3 = párpado superior
            P5, P6 = párpado inferior

    Returns:
        float: valor EAR (0.0 - 0.5 aprox.)
    """
    # Distancias verticales (párpado superior - párpado inferior)
    vertical_1 = distance(eye_points[1], eye_points[5])  # |P2-P6|
    vertical_2 = distance(eye_points[2], eye_points[4])  # |P3-P5|

    # Distancia horizontal (esquina a esquina)
    horizontal = distance(eye_points[0], eye_points[3])   # |P1-P4|

    # Evitar división por cero
    if horizontal == 0:
        return 0.0

    ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
    return ear


def compute_avg_ear(left_eye, right_eye):
    """
    Promedio de EAR de ambos ojos.
    ¿Por qué promediar? Porque a veces un ojo parpadea ligeramente
    diferente al otro, o la luz afecta más a un lado.
    """
    left_ear = compute_ear(left_eye)
    right_ear = compute_ear(right_eye)
    return (left_ear + right_ear) / 2.0, left_ear, right_ear
