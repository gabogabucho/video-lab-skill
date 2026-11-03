#!/usr/bin/env bash
# Mezcla final. Sección 12 de la guía.
# El preset por defecto es slow. VIDEO_LAB_X264_PRESET lo puede cambiar.
#
#   componer.sh CAPA_VIDEO CAPA_GRAFICOS VOZ EFECTOS SALIDA DURACION
#   componer.sh --solo-grafico GRAFICOS VOZ EFECTOS SALIDA DURACION
set -euo pipefail

PRESET="${VIDEO_LAB_X264_PRESET:-slow}"

audio_filter() {
  # $1 es el índice de la voz, $2 el de los efectos.
  local voz="$1" sfx="$2"
  printf '%s' \
"[${voz}:a]aresample=48000,aformat=channel_layouts=mono,apad,asplit=2[vo][sc];\
[${sfx}:a]aresample=48000,volume=0.42[s];\
[s][sc]sidechaincompress=threshold=0.04:ratio=3:attack=10:release=250[sd];\
[vo][sd]amix=inputs=2:normalize=0:duration=longest,\
loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,pan=stereo|c0=c0|c1=c0[a]"
}

if [[ "${1:-}" == "--solo-grafico" ]]; then
  shift
  if [[ $# -ne 5 ]]; then
    echo "Uso: componer.sh --solo-grafico GRAFICOS.mp4 VOZ.wav EFECTOS.wav SALIDA.mp4 DURACION" >&2
    exit 2
  fi
  # Video solo gráfico: la entrada 0 ya es la imagen y se saca el overlay.
  ffmpeg -y -loglevel error \
    -i "$1" -i "$2" -i "$3" \
    -filter_complex "$(audio_filter 1 2)" \
    -map "0:v:0" -map "[a]" \
    -c:v libx264 -crf 16 -preset "$PRESET" -c:a aac -b:a 192k \
    -t "$5" -movflags +faststart "$4"
  exit 0
fi

if [[ $# -ne 6 ]]; then
  echo "Uso: componer.sh CAPA_VIDEO CAPA_GRAFICOS VOZ EFECTOS SALIDA DURACION" >&2
  exit 2
fi

ffmpeg -y -loglevel error \
  -i "$1" -i "$2" -i "$3" -i "$4" \
  -filter_complex "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v];$(audio_filter 2 3)" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -crf 16 -preset "$PRESET" -c:a aac -b:a 192k \
  -t "$6" -movflags +faststart "$5"
