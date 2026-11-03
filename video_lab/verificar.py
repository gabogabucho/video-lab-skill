"""Comprueba que estén las herramientas de la guía. Lo corre setup.sh al final."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from video_lab.marca import verificar_fuente
from video_lab.normalizar import VF_HDR
from video_lab.paths import ruta_fuente, ruta_yunet


FILTROS = (
    "zscale",
    "tonemap",
    "overlay",
    "loudnorm",
    "silencedetect",
    "sidechaincompress",
    "afftdn",
    "acompressor",
    "highpass",
    "zoompan",
    "eq",
    "lut3d",
    "drawbox",
    "tile",
    "chromakey",
    "ebur128",
    "scale",
    "fps",
    "crop",
    "amix",
    "apad",
    "aresample",
    "volume",
)
CODECS = ("libx264", "aac", "pcm_s16le", "qtrle")


def _exigir(ok: bool, mensaje: str) -> None:
    if not ok:
        raise SystemExit(mensaje)
    print(f"ok  {mensaje}")


def _ffmpeg() -> None:
    for binario in ("ffmpeg", "ffprobe"):
        _exigir(shutil.which(binario) is not None, binario)
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], text=True, capture_output=True)
    nombres = set()
    for linea in proc.stdout.splitlines():
        partes = linea.split()
        if len(partes) >= 2:
            nombres.add(partes[1])
    faltan = [f for f in FILTROS if f not in nombres]
    _exigir(not faltan, "filtros de ffmpeg" if not faltan else f"faltan filtros: {', '.join(faltan)}")
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], text=True, capture_output=True)
    faltan_c = [c for c in CODECS if c not in proc.stdout]
    _exigir(not faltan_c, "codecs" if not faltan_c else f"faltan codecs: {', '.join(faltan_c)}")


def _cadena_hdr() -> None:
    vf = VF_HDR.format(fps=30)
    with tempfile.TemporaryDirectory(prefix="video-lab-hdr-") as tmp:
        src = Path(tmp) / "tag.mp4"
        # Un gris etiquetado como PQ, de dos cuadros, para ver que la cadena HDR corre.
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=gray:s=64x64:r=30:d=0.1",
                "-frames:v",
                "2",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-color_primaries",
                "bt2020",
                "-color_trc",
                "smpte2084",
                "-colorspace",
                "bt2020nc",
                str(src),
            ],
            check=True,
        )
        proc = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", vf, "-frames:v", "2", "-f", "null", "-"],
            text=True,
            capture_output=True,
        )
    _exigir(proc.returncode == 0, "cadena HDR (zscale + tonemap)" if proc.returncode == 0 else proc.stderr[-1500:])


def _imports() -> None:
    import cv2
    import fontTools
    import PIL
    import playwright
    from faster_whisper import WhisperModel

    _exigir(callable(WhisperModel), "faster-whisper importable")
    _exigir(hasattr(cv2, "FaceDetectorYN"), "cv2.FaceDetectorYN")
    del fontTools, PIL, playwright


def _yunet() -> None:
    import cv2

    modelo = ruta_yunet()
    _exigir(modelo.exists(), f"modelo de caras {modelo}" if modelo.exists() else f"falta {modelo}. Corré bash scripts/setup.sh")
    img = np.zeros((240, 320, 3), np.uint8)
    det = cv2.FaceDetectorYN.create(str(modelo), "", (320, 240))
    det.setInputSize((320, 240))
    det.detect(img)
    print("ok  YuNet detecta (cuadro vacío, sin caras)")


def _fuente() -> None:
    fuente = ruta_fuente()
    _exigir(fuente.exists(), f"fuente {fuente}" if fuente.exists() else f"falta {fuente}. Corré bash scripts/setup.sh")
    verificar_fuente(fuente)
    print(f"ok  fuente con ¿¡áéíóúñ  ({fuente.name})")


def _chromium() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        exe = Path(p.chromium.executable_path)
        _exigir(exe.exists(), f"Chromium {exe}" if exe.exists() else f"falta Chromium. Corré bash scripts/setup.sh")
        browser = p.chromium.launch(args=["--disable-gpu"])
        browser.close()
    print("ok  Chromium abre y cierra")


def main() -> int:
    _ffmpeg()
    _cadena_hdr()
    _imports()
    _fuente()
    _yunet()
    _chromium()
    print("verificación lista")
    return 0


if __name__ == "__main__":
    sys.exit(main())
