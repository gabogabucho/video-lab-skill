"""Transcripción, silencios, escenas y caras. Sección 6.2.

Se calcula una vez y se guarda. Volver a correr este script borra la marca de
revisión humana: la transcripción nueva hay que leerla otra vez.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from video_lab.paths import ruta_yunet

_SILENCIO = re.compile(r"silence_(start|end): ([0-9.]+)")
_ESCENA = re.compile(r"pts_time:([0-9.]+)")


def _stem_de(path: Path) -> str:
    return path.stem


def transcribir(mov: Path, destino: Path, idioma: str) -> list[dict]:
    import tempfile

    from faster_whisper import WhisperModel

    with tempfile.TemporaryDirectory(prefix="video-lab-") as tmp:
        wav = Path(tmp) / "voz.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mov), "-ar", "16000", "-ac", "1", str(wav)],
            check=True,
        )
        with wave.open(str(wav)) as w:
            audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        modelo = os.environ.get("WHISPER_MODEL", "small")
        device = os.environ.get("WHISPER_DEVICE", "cpu")
        compute = os.environ.get("WHISPER_COMPUTE", "int8")
        print(f"transcribiendo con {modelo} ({device}, {compute})…", file=sys.stderr)
        model = WhisperModel(modelo, device=device, compute_type=compute)
        segs, _ = model.transcribe(audio, language=idioma, word_timestamps=True)
        palabras = []
        for s in segs:
            for x in s.words or []:
                palabras.append({"w": x.word.strip(), "a": round(x.start, 3), "b": round(x.end, 3)})
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(palabras, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(
        f"Transcripción en {destino}. Revisala a mano antes de subtitular "
        "(nombres, modismos, números).",
        file=sys.stderr,
    )
    return palabras


def silencios(mov: Path, txt: Path, js: Path) -> list[dict]:
    proc = subprocess.run(
        ["ffmpeg", "-i", str(mov), "-af", "silencedetect=noise=-35dB:d=0.25", "-f", "null", "-"],
        text=True,
        capture_output=True,
    )
    lineas = [f"silence_{k}: {v}" for k, v in _SILENCIO.findall(proc.stderr)]
    txt.parent.mkdir(parents=True, exist_ok=True)
    txt.write_text("\n".join(lineas) + ("\n" if lineas else ""), encoding="utf-8")
    pares: list[dict] = []
    actual = None
    for k, v in _SILENCIO.findall(proc.stderr):
        if k == "start":
            actual = float(v)
        elif k == "end" and actual is not None:
            pares.append({"a": actual, "b": float(v)})
            actual = None
    js.write_text(json.dumps(pares, indent=1) + "\n", encoding="utf-8")
    return pares


def escenas(mov: Path, txt: Path, js: Path) -> list[float]:
    proc = subprocess.run(
        ["ffmpeg", "-i", str(mov), "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"],
        text=True,
        capture_output=True,
    )
    tiempos = [float(x) for x in _ESCENA.findall(proc.stderr)]
    txt.write_text("".join(f"pts_time:{t}\n" for t in tiempos), encoding="utf-8")
    js.write_text(json.dumps(tiempos, indent=1) + "\n", encoding="utf-8")
    return tiempos


def caras(mov: Path, destino: Path, modelo: Path) -> list[dict]:
    import cv2

    if not modelo.exists():
        raise SystemExit(
            f"No está el modelo de caras: {modelo}\nCorré bash scripts/setup.sh"
        )
    cap = cv2.VideoCapture(str(mov))
    if not cap.isOpened():
        raise SystemExit(f"OpenCV no pudo abrir {mov}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(3))
    h = int(cap.get(4))
    det = cv2.FaceDetectorYN.create(str(modelo), "", (0, 0))
    det.setInputSize((w, h))
    xs: list[dict] = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % 3 == 0:
            res = det.detect(frame)
            caras_arr = res[1] if isinstance(res, tuple) else res
            if caras_arr is None or len(caras_arr) == 0:
                cx = None
            else:
                cx = float(caras_arr[0][0] + caras_arr[0][2] / 2)
            xs.append({"t": round(i / fps, 3), "cx": cx})
        i += 1
    cap.release()
    if not xs:
        destino.write_text("[]\n", encoding="utf-8")
        return []
    vals = np.array([p["cx"] if p["cx"] is not None else np.nan for p in xs], dtype=float)
    idx = np.arange(len(vals))
    okm = ~np.isnan(vals)
    if not okm.any():
        print(f"aviso: no se detectó ninguna cara en {mov.name}; cx queda al centro", file=sys.stderr)
        vals = np.full(len(vals), w / 2.0)
    else:
        vals = np.interp(idx, idx[okm], vals[okm])
        vals = np.convolve(vals, np.ones(15) / 15, mode="same")
    salida = [{"t": p["t"], "cx": round(float(v), 1)} for p, v in zip(xs, vals)]
    destino.write_text(json.dumps(salida, indent=1) + "\n", encoding="utf-8")
    return salida


def _borrar_revision(analisis: Path) -> None:
    marca = analisis / "transcripcion.revisada"
    if marca.exists():
        marca.unlink()
    (analisis / "transcripcion.revision.json").write_text(
        json.dumps(
            {
                "revisada": False,
                "motivo": "Revisar nombres, modismos y números antes de usar la transcripción en subtítulos.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def analizar_uno(mov: Path, analisis: Path, modelo: Path, idioma: str, con_transcripcion: bool) -> None:
    analisis.mkdir(parents=True, exist_ok=True)
    stem = _stem_de(mov)
    print(f"analizando {mov.name}")
    if con_transcripcion:
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        transcribir(mov, analisis / f"{stem}.palabras.json", idioma)
        _borrar_revision(analisis)
    silencios(mov, analisis / f"{stem}.silencios.txt", analisis / f"{stem}.silencios.json")
    escenas(mov, analisis / f"{stem}.escenas.txt", analisis / f"{stem}.escenas.json")
    caras(mov, analisis / f"{stem}.cara.json", modelo)
    print(f"listo     {analisis}/{stem}.*")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analizar un intermedio ya normalizado.")
    ap.add_argument("entrada", nargs="?", type=Path)
    ap.add_argument("--proyecto", type=Path, default=Path("."))
    ap.add_argument("--idioma", default="es")
    ap.add_argument("--sin-transcripcion", action="store_true")
    ap.add_argument("--modelo", type=Path, default=None)
    args = ap.parse_args(argv)
    proyecto = args.proyecto.resolve()
    modelo = args.modelo or ruta_yunet()
    analisis = proyecto / "analisis"
    if args.entrada:
        src = args.entrada if args.entrada.is_absolute() else proyecto / args.entrada
        analizar_uno(src, analisis, modelo, args.idioma, not args.sin_transcripcion)
        return 0
    archivos = sorted((proyecto / "trabajo").glob("*.mov"))
    if not archivos:
        raise SystemExit("No hay archivos en trabajo/. Normalizá primero.")
    for src in archivos:
        analizar_uno(src, analisis, modelo, args.idioma, not args.sin_transcripcion)
    return 0


if __name__ == "__main__":
    sys.exit(main())
