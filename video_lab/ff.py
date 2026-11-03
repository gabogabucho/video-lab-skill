"""Llamadas a ffmpeg y ffprobe."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        mostrado = " ".join(cmd[:8])
        cola = (proc.stderr or proc.stdout or "")[-4000:]
        raise SystemExit(f"Falló: {mostrado}\n{cola}")
    return proc


def probe(path: Path) -> dict:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"ffprobe no pudo leer {path}\n{(proc.stderr or '')[-2000:]}")
    return json.loads(proc.stdout)


def streams(path: Path, tipo: str) -> list[dict]:
    return [s for s in probe(path).get("streams", []) if s.get("codec_type") == tipo]


def tiene_audio(path: Path) -> bool:
    return bool(streams(path, "audio"))


def fps_de(stream: dict) -> float:
    raw = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1"
    num, _, den = raw.partition("/")
    den_f = float(den or 1)
    if den_f == 0:
        return 0.0
    return float(num) / den_f
