"""Pasa el crudo a un intermedio estable. Sección 6.1.

Supuesto: `-ss` no se usa acá. La rotación de displaymatrix la aplica ffmpeg
por su cuenta (no pasamos -noautorotate), que es lo que hace el comando de la guía.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from video_lab.ff import fps_de, probe, run, streams, tiene_audio

# Cadena HDR de la guía, con el fps al final.
VF_HDR = (
    "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
    "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,fps={fps}"
)
# Si no es HDR, la guía se queda con fps constante y yuv420p.
VF_SDR = "fps={fps},format=yuv420p"

_HDR = {"smpte2084", "arib-std-b67", "smpte428"}


def es_hdr(info: dict) -> bool:
    for s in info.get("streams", []):
        if s.get("color_transfer") in _HDR:
            return True
    return False


def _ya_esta(dst: Path, fps: int) -> bool:
    if not dst.exists():
        return False
    info = probe(dst)
    video = streams(dst, "video")
    audio = streams(dst, "audio")
    if not video or not audio:
        return False
    if video[0].get("pix_fmt") != "yuv420p":
        return False
    if abs(fps_de(video[0]) - fps) > 0.05:
        return False
    if audio[0].get("codec_name") != "pcm_s16le":
        return False
    if int(audio[0].get("sample_rate") or 0) != 48000:
        return False
    if es_hdr(info):
        return False
    return True


def normalizar(src: Path, dst: Path, fps: int = 30, forzar: bool = False) -> None:
    if not src.exists():
        raise SystemExit(f"No está el crudo: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not forzar and dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime and _ya_esta(dst, fps):
        print(f"ya normalizado  {dst}")
        return

    info = probe(src)
    video = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if not video:
        raise SystemExit(f"{src} no tiene video.")
    hdr = es_hdr(info)
    vf = (VF_HDR if hdr else VF_SDR).format(fps=fps)
    print(f"{'HDR' if hdr else 'SDR'}  {src.name}  →  {dst}")

    cmd = ["ffmpeg", "-y", "-i", str(src)]
    dur = float(info.get("format", {}).get("duration") or video[0].get("duration") or 0)
    sin_audio = not tiene_audio(src)
    if sin_audio:
        # La guía asume audio. Si no hay, se agrega silencio para que el intermedio
        # siempre tenga pcm_s16le y la concatenación no se rompa.
        if dur <= 0:
            raise SystemExit(f"No pude medir la duración de {src}.")
        cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=channel_layout=mono:sample_rate=48000"]
    cmd += [
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        "12",
        "-preset",
        "slow",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "48000",
    ]
    if sin_audio:
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-shortest"]
    cmd.append(str(dst))
    run(cmd)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Normalizar crudo a 30 fps, SDR, yuv420p, pcm.")
    ap.add_argument("entrada", nargs="?", type=Path, help="Un archivo. Si falta, se usa crudo/ del proyecto.")
    ap.add_argument("-o", "--salida", type=Path, help="Salida .mov. Por defecto trabajo/<nombre>.mov")
    ap.add_argument("--proyecto", type=Path, default=Path("."))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--forzar", action="store_true")
    args = ap.parse_args(argv)
    proyecto = args.proyecto.resolve()

    if args.entrada:
        src = args.entrada if args.entrada.is_absolute() else proyecto / args.entrada
        if args.salida:
            dst = args.salida if args.salida.is_absolute() else proyecto / args.salida
        else:
            dst = proyecto / "trabajo" / f"{src.stem}.mov"
        normalizar(src, dst, fps=args.fps, forzar=args.forzar)
        return 0

    crudo = proyecto / "crudo"
    archivos = [
        p
        for p in sorted(crudo.glob("*"))
        if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
    ]
    if not archivos:
        raise SystemExit(f"No hay videos en {crudo}.")
    for src in archivos:
        normalizar(src, proyecto / "trabajo" / f"{src.stem}.mov", fps=args.fps, forzar=args.forzar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
