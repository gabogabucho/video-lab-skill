"""Rutas del skill y caracteres que toda fuente tiene que cubrir."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Los mismos que exige la guía al verificar una fuente.
CARACTERES = "¿¡áéíóúñÁÉÍÓÚÑü·"


def ruta_yunet() -> Path:
    env = os.environ.get("VIDEO_LAB_YUNET")
    if env:
        return Path(env).expanduser()
    return ROOT / "share" / "models" / "face_detection_yunet.onnx"


def ruta_fuente() -> Path:
    env = os.environ.get("VIDEO_LAB_FONT")
    if env:
        return Path(env).expanduser()
    return ROOT / "share" / "fonts" / "texto.ttf"
