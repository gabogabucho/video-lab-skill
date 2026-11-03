#!/usr/bin/env bash
# Render corto de punta a punta. Tiene que dejar un MP4.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "No está el entorno. Corré: bash scripts/setup.sh" >&2
  exit 1
fi

export HF_HUB_DISABLE_TELEMETRY=1
# El MP4 de humo dura 2 segundos. veryfast alcanza para la prueba;
# un video de verdad usa el preset slow de la guía.
export VIDEO_LAB_X264_PRESET="${VIDEO_LAB_X264_PRESET:-veryfast}"

log() { printf '\n→ %s\n' "$*"; }

log "pruebas de las funciones"
"$PY" -m video_lab.selftest

DEST="$ROOT/out/smoke"
rm -rf "$DEST"
mkdir -p "$DEST/crudo" "$DEST/proyecto"

log "normalizar un crudo sintético (24 fps → 30, aac → pcm)"
ffmpeg -y -loglevel error \
  -f lavfi -i "testsrc=size=320x240:rate=24:duration=1" \
  -f lavfi -i "sine=frequency=440:sample_rate=44100:duration=1" \
  -shortest -c:v libx264 -preset veryfast -c:a aac \
  "$DEST/crudo/toma.mp4"
"$PY" -m video_lab.normalizar "$DEST/crudo/toma.mp4" -o "$DEST/trabajo.mov" --proyecto "$DEST"
"$PY" - << PY
from pathlib import Path
from video_lab.ff import fps_de, streams
p = Path("$DEST/trabajo.mov")
v, a = streams(p, "video")[0], streams(p, "audio")[0]
assert v["pix_fmt"] == "yuv420p", v["pix_fmt"]
assert abs(fps_de(v) - 30) < 0.05, fps_de(v)
assert a["codec_name"] == "pcm_s16le", a["codec_name"]
assert int(a["sample_rate"]) == 48000
print("normalizar ok", v["width"], v["height"], round(fps_de(v), 2), a["codec_name"])
PY

log "normalizar de nuevo (tiene que decir que ya está)"
"$PY" -m video_lab.normalizar "$DEST/crudo/toma.mp4" -o "$DEST/trabajo.mov" --proyecto "$DEST"

log "proyecto de humo"
cp -a "$ROOT/examples/humo/." "$DEST/proyecto/"
"$PY" -m video_lab.marca verificar --proyecto "$DEST/proyecto"

log "render, efectos y mezcla"
"$PY" -m video_lab.entregar --proyecto "$DEST/proyecto" --salida "$DEST/smoke.mp4" --fondo

"$PY" - << PY
import json, subprocess
from pathlib import Path
video = Path("$DEST/smoke.mp4")
hoja = Path("$DEST/proyecto/out/hoja.png")
assert video.exists() and video.stat().st_size > 20_000, video.stat().st_size
assert hoja.exists() and hoja.stat().st_size > 1000
info = json.loads(subprocess.check_output(
    ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(video)], text=True))
tipos = {s["codec_type"] for s in info["streams"]}
assert tipos >= {"video", "audio"}, tipos
v = next(s for s in info["streams"] if s["codec_type"] == "video")
assert int(v["width"]) == 540 and int(v["height"]) == 960
assert v["codec_name"] == "h264"
dur = float(v["duration"])
assert 1.7 <= dur <= 2.3, dur
mudo = Path("$DEST/smoke_sin_audio.mp4")
efectos = Path("$DEST/proyecto/out/efectos.wav")
assert mudo.exists() and efectos.exists()
print(f"SMOKE OK  {video}  {dur:.3f}s  {video.stat().st_size} bytes")
PY
