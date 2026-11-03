"""Control de calidad. Sección 13.

La hoja de contactos dibuja la zona segura. En un video largo el paso es de
60 cuadros, como la guía. Si el video es corto, el paso se achica para que
la hoja tenga entre 4 y 8 cuadros y no salga vacía.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from video_lab.ff import probe, run, streams
from video_lab.guion import cargar, duracion_de
from video_lab.zonas import drawbox_hoja, zona_para

_CHECKLIST = """
Revisión humana:
- Ningún texto toca el borde de la zona segura (el rectángulo rojo de la hoja).
- No hay cuadros vacíos ni negros en los cortes.
- Los acentos, signos y números se ven bien, con formato local.
- Los momentos clave caen en su palabra. Escuchar con auriculares.
- La marca se pronuncia bien. Si una voz generada la dice mal, se escribe fonética o con una pausa antes.
- En video crudo: el encuadre no tiembla, la cara no queda cortada y los jump cuts no muerden sílabas.
- Los subtítulos coinciden palabra por palabra con lo que se dice.
"""


def _frames(video: Path) -> dict:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames,duration,width,height,codec_name",
            "-of",
            "json",
            str(video),
        ],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"ffprobe no pudo contar cuadros de {video}\n{proc.stderr[-1500:]}")
    data = json.loads(proc.stdout)
    return data["streams"][0]


def loudness(video: Path) -> float | None:
    proc = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(video), "-af", "ebur128", "-f", "null", "-"],
        text=True,
        capture_output=True,
    )
    cola = proc.stderr
    idx = cola.rfind("Summary:")
    trozo = cola[idx:] if idx >= 0 else cola
    hallados = re.findall(r"I:\s*(-?[0-9.]+)", trozo)
    if not hallados:
        return None
    return float(hallados[-1])


def _tiempos(duracion: float, nb: int) -> list[float]:
    if duracion <= 0 or nb <= 0:
        return [0.0]
    # La guía toma un cuadro cada 60. En un video de menos de ~8 s eso deja
    # uno solo, así que se reparte la hoja en hasta 8 instantes.
    if nb >= 480:
        paso = 60
        n = min(12, nb // paso)
    else:
        n = min(8, max(4, nb // 2 if nb >= 8 else nb))
    return [min(duracion - 0.04, (i + 0.5) * duracion / n) for i in range(n)]


def hoja_contactos(video: Path, ancho: int, alto: int, destino: Path) -> None:
    zona = zona_para(ancho, alto)
    tw = 270
    th = max(2, int(round(alto * (tw / ancho))))
    x, y, bw, bh = drawbox_hoja(zona, tw, th)
    info = _frames(video)
    dur = float(info.get("duration") or 0)
    nb = int(info.get("nb_read_frames") or 0)
    tiempos = _tiempos(dur, nb)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="video-lab-hoja-") as tmp:
        base = Path(tmp)
        n = len(tiempos)
        cols = 4 if n > 4 else n
        rows = max(1, math.ceil(n / cols))
        need = cols * rows
        vf = f"scale={tw}:{th},drawbox=x={x}:y={y}:w={bw}:h={bh}:color=red@0.8:t=2"
        for i, t in enumerate(tiempos):
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{t:.3f}",
                    "-i",
                    str(video),
                    "-frames:v",
                    "1",
                    "-vf",
                    vf,
                    str(base / f"{i:02d}.png"),
                ]
            )
        for i in range(n, need):
            shutil.copy(base / f"{n - 1:02d}.png", base / f"{i:02d}.png")
        run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                "1",
                "-i",
                str(base / "%02d.png"),
                "-frames:v",
                "1",
                "-vf",
                f"tile={cols}x{rows}:padding=6:margin=6:color=white",
                str(destino),
            ]
        )
    print(f"hoja     {destino}")


def revisar(video: Path, ancho: int, alto: int, fps: float, duracion: float, hoja: Path) -> None:
    if not video.exists():
        raise SystemExit(f"No está el video: {video}")
    info = probe(video)
    v = streams(video, "video")
    a = streams(video, "audio")
    if not v:
        raise SystemExit("El archivo no tiene pista de video.")
    if not a:
        raise SystemExit("El archivo no tiene pista de audio.")
    contados = _frames(video)
    nb = int(contados.get("nb_read_frames") or 0)
    dur_v = float(contados.get("duration") or v[0].get("duration") or 0)
    dur_a = float(a[0].get("duration") or 0)
    esperado = fps * duracion
    print(f"video    {contados.get('codec_name')} {contados.get('width')}×{contados.get('height')}  {nb} cuadros  {dur_v:.3f}s")
    print(f"audio    {a[0].get('codec_name')}  {dur_a:.3f}s  {a[0].get('sample_rate')} Hz")
    if nb and abs(nb - esperado) > 2:
        raise SystemExit(f"Cuadros {nb}, se esperaban ~{esperado:.0f} ({fps} fps × {duracion} s).")
    if abs(dur_v - duracion) > max(0.15, 2 / fps):
        raise SystemExit(f"Duración de video {dur_v:.3f}s, el guion pide {duracion:.3f}s.")
    if abs(dur_a - dur_v) > 0.25:
        raise SystemExit(f"El audio ({dur_a:.3f}s) no coincide con el video ({dur_v:.3f}s).")
    if int(contados.get("width") or 0) != ancho or int(contados.get("height") or 0) != alto:
        raise SystemExit(
            f"Tamaño {contados.get('width')}×{contados.get('height')}, el guion pide {ancho}×{alto}."
        )
    i = loudness(video)
    if i is None:
        print("loudness  (no pude leer I:)")
    else:
        print(f"loudness  I: {i:.1f} LUFS  (objetivo ≈ -14)")
        if duracion >= 8 and not (-18.0 <= i <= -10.0):
            raise SystemExit(
                f"Loudness {i:.1f} LUFS lejos de -14. Revisá la mezcla antes de entregar."
            )
    hoja_contactos(video, ancho, alto, hoja)
    print(_CHECKLIST)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chequear un MP4 y armar la hoja de contactos.")
    ap.add_argument("--proyecto", type=Path, default=Path("."))
    ap.add_argument("--video", type=Path, default=None)
    ap.add_argument("--hoja", type=Path, default=None)
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--duracion", type=float, default=None)
    ap.add_argument("--ancho", type=int, default=None)
    ap.add_argument("--alto", type=int, default=None)
    args = ap.parse_args(argv)
    proyecto = args.proyecto.resolve()
    guion = None
    guion_path = proyecto / "guion.json"
    if guion_path.exists():
        guion = cargar(guion_path)
    video = args.video or (proyecto / "out" / "final.mp4")
    if not video.is_absolute():
        video = proyecto / video
    hoja = args.hoja or (proyecto / "out" / "hoja.png")
    if not hoja.is_absolute():
        hoja = proyecto / hoja
    if guion:
        fmt = guion["formato"]
        ancho = args.ancho or int(fmt["w"])
        alto = args.alto or int(fmt["h"])
        fps = args.fps or float(fmt["fps"])
        duracion = args.duracion if args.duracion is not None else duracion_de(guion)
    else:
        if None in (args.ancho, args.alto, args.fps, args.duracion):
            raise SystemExit("Sin guion.json hacen falta --ancho --alto --fps --duracion.")
        ancho, alto, fps, duracion = args.ancho, args.alto, args.fps, args.duracion
    revisar(video, ancho, alto, fps, duracion, hoja)
    return 0


if __name__ == "__main__":
    sys.exit(main())
