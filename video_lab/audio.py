"""Voz: silencio, extracción y la limpieza de la sección 6.6."""

from __future__ import annotations

import wave
from pathlib import Path

from video_lab.ff import run

# El loudnorm de esta pasada deja la voz pareja. El de la mezcla (sección 12) es el final.
FILTRO_LIMPIEZA = (
    "highpass=f=80,afftdn=nf=-25,"
    "acompressor=threshold=-18dB:ratio=3:attack=5:release=120,"
    "loudnorm=I=-16:TP=-1.5"
)


def escribir_silencio(path: Path, duracion: float, sr: int = 48000) -> None:
    n = max(1, int(round(sr * duracion)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"\x00\x00" * n)


def a_wav(src: Path, dst: Path, limpiar: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(src), "-vn"]
    if limpiar:
        cmd += ["-af", FILTRO_LIMPIEZA]
    cmd += ["-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(dst)]
    run(cmd)


def resolver_voz(guion: dict, proyecto: Path, capa_video: Path | None, dst: Path, duracion: float) -> None:
    audio = guion.get("audio") or {}
    voz = audio.get("voz")
    limpiar = bool(audio.get("limpieza"))
    if voz in (None, "", "ninguna", "silencio"):
        escribir_silencio(dst, duracion)
        print(f"voz      silencio  {dst.name}")
        return
    if voz == "fuente":
        if capa_video is None or not capa_video.exists():
            raise SystemExit('audio.voz es "fuente" y no hay capa de video.')
        src = capa_video
    else:
        src = proyecto / str(voz)
        if not src.exists():
            raise SystemExit(f"No está el archivo de voz: {src}")
    a_wav(src, dst, limpiar=limpiar)
    print(f"voz      {'limpia' if limpiar else 'tal cual'}  {dst.name}")
