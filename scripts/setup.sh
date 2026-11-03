#!/usr/bin/env bash
# Instala y verifica las herramientas de la guía. Se puede correr de nuevo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FONT_URL="https://github.com/notofonts/notofonts.github.io/raw/main/fonts/NotoSans/full/ttf/NotoSans-ExtraBold.ttf"
FONT_SHA="678c30c8d959caa7b71dea8bfca5d2c46a5e1107d4f7a1ea3863ce51705a5fab"
OFL_URL="https://raw.githubusercontent.com/notofonts/latin-greek-cyrillic/main/OFL.txt"
YUNET_URL="https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
YUNET_SHA="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"

log() { printf '\n→ %s\n' "$*"; }

pkg_ok() { dpkg -s "$1" >/dev/null 2>&1; }

PY_MM="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PAQUETES=(ffmpeg python3 python3-pip python3-venv "python${PY_MM}-venv" curl ca-certificates)
FALTAN=()
for pkg in "${PAQUETES[@]}"; do
  pkg_ok "$pkg" || FALTAN+=("$pkg")
done
if ((${#FALTAN[@]})); then
  log "instalando paquetes del sistema: ${FALTAN[*]}"
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${FALTAN[@]}"
else
  log "paquetes del sistema ya están"
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  log "creando .venv"
  rm -rf "$ROOT/.venv"
  python3 -m venv "$ROOT/.venv"
fi
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
python -m pip install -q -U pip
log "instalando el paquete (idempotente)"
python -m pip install -q -e "$ROOT"

log "Chromium de Playwright"
python -m playwright install chromium
if ! python -m playwright install-deps chromium; then
  log "install-deps pidió root, reintento con sudo"
  sudo "$ROOT/.venv/bin/python" -m playwright install-deps chromium
fi

bajar() {
  local url="$1" dest="$2" sha="$3"
  mkdir -p "$(dirname "$dest")"
  if [[ -s "$dest" ]] && [[ "$(sha256sum "$dest" | awk '{print $1}')" == "$sha" ]]; then
    log "ya está $(basename "$dest")"
    return
  fi
  log "bajando $(basename "$dest")"
  curl -fsSL --retry 3 --retry-delay 2 -o "${dest}.partial" "$url"
  local got
  got="$(sha256sum "${dest}.partial" | awk '{print $1}')"
  if [[ "$got" != "$sha" ]]; then
    echo "Hash inesperado de $dest" >&2
    echo "  esperado $sha" >&2
    echo "  obtenido $got" >&2
    rm -f "${dest}.partial"
    exit 1
  fi
  mv "${dest}.partial" "$dest"
}

bajar "$FONT_URL" "$ROOT/share/fonts/texto.ttf" "$FONT_SHA"
if [[ ! -s "$ROOT/share/fonts/OFL.txt" ]]; then
  log "bajando licencia OFL de Noto Sans"
  curl -fsSL --retry 3 -o "$ROOT/share/fonts/OFL.txt" "$OFL_URL"
fi
if ! grep -q "Open Font License" "$ROOT/share/fonts/OFL.txt"; then
  echo "OFL.txt no parece la licencia SIL." >&2
  exit 1
fi
bajar "$YUNET_URL" "$ROOT/share/models/face_detection_yunet.onnx" "$YUNET_SHA"

for dest in \
  "$ROOT/templates/proyecto/brand/fonts/texto.ttf" \
  "$ROOT/examples/humo/brand/fonts/texto.ttf"
do
  if [[ ! -s "$dest" ]] || ! cmp -s "$ROOT/share/fonts/texto.ttf" "$dest"; then
    mkdir -p "$(dirname "$dest")"
    cp "$ROOT/share/fonts/texto.ttf" "$dest"
  fi
done

python -m video_lab.marca logo-demo "$ROOT/templates/proyecto/brand/logo.png"
python -m video_lab.marca logo-demo "$ROOT/examples/humo/brand/logo.png"

if [[ "${1:-}" == "--prefetch-whisper" ]]; then
  log "bajando el modelo de faster-whisper (WHISPER_MODEL=${WHISPER_MODEL:-small})"
  HF_HUB_DISABLE_TELEMETRY=1 python - << 'PY'
import os
from faster_whisper import WhisperModel
WhisperModel(
    os.environ.get("WHISPER_MODEL", "small"),
    device=os.environ.get("WHISPER_DEVICE", "cpu"),
    compute_type=os.environ.get("WHISPER_COMPUTE", "int8"),
)
print("modelo listo")
PY
fi

log "verificando"
python -m video_lab.verificar
log "setup listo"
