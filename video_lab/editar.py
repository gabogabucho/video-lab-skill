"""Propuesta de jump cuts y construcción de la capa de video. Secciones 6.3 a 6.5.

`proponer` escribe una propuesta y no toca el guion.
`construir` lee la edición que ya está en el guion.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from video_lab.ff import run
from video_lab.guion import cargar
from video_lab.mapa import construir_mapa, palabras_en_final

AIRE = 0.08  # dentro del rango 0,05–0,10 s que pide la guía
_MULETILLAS = {"eh", "este"}


def _norm(palabra: str) -> str:
    return palabra.strip().strip(".,;:!?¡¿\"'“”«»").lower()


def proponer_tramos(
    palabras: list[dict],
    silencios: list[dict],
    duracion: float,
    fuente: str,
    aire: float = AIRE,
) -> list[dict]:
    """Tramos que saltan silencios largos y muletillas. No decide la toma."""
    muletilla: list[tuple[float, float]] = []
    i = 0
    while i < len(palabras):
        w = _norm(str(palabras[i]["w"]))
        if w in _MULETILLAS:
            muletilla.append((float(palabras[i]["a"]), float(palabras[i]["b"])))
            i += 1
            continue
        if (
            w == "o"
            and i + 1 < len(palabras)
            and _norm(str(palabras[i + 1]["w"])) == "sea"
        ):
            muletilla.append((float(palabras[i]["a"]), float(palabras[i + 1]["b"])))
            i += 2
            continue
        i += 1

    def es_muletilla(a: float, b: float) -> bool:
        return any(x <= a + 1e-3 and y >= b - 1e-3 for x, y in muletilla)

    speech: list[tuple[float, float]] = []
    for p in palabras:
        a, b = float(p["a"]), float(p["b"])
        if es_muletilla(a, b):
            continue
        speech.append((a, b))
    speech.sort()
    fusion: list[tuple[float, float]] = []
    for a, b in speech:
        if fusion and a - fusion[-1][1] < 0.12:
            fusion[-1] = (fusion[-1][0], max(fusion[-1][1], b))
        else:
            fusion.append((a, b))

    expandido: list[tuple[float, float]] = []
    for a, b in fusion:
        expandido.append((max(0.0, a - aire), min(duracion, b + aire)))
    expandido.sort()
    unidos: list[tuple[float, float]] = []
    for a, b in expandido:
        if unidos and a <= unidos[-1][1] + 1e-6:
            unidos[-1] = (unidos[-1][0], max(unidos[-1][1], b))
        else:
            unidos.append((a, b))

    edicion = []
    for a, b in unidos:
        if b - a <= 0.02:
            continue
        edicion.append(
            {
                "fuente": fuente,
                "in": round(a, 3),
                "out": round(b, 3),
                "velocidad": 1.0,
                "encuadre": "centro",
            }
        )
    return edicion


def _atempo(velocidad: float) -> str:
    if velocidad <= 0:
        raise SystemExit("velocidad inválida")
    factores: list[float] = []
    falta = velocidad
    while falta > 100.0:
        factores.append(100.0)
        falta /= 100.0
    while falta < 0.5:
        factores.append(0.5)
        falta /= 0.5
    factores.append(falta)
    return ",".join(f"atempo={f:.6f}" for f in factores)


def _ventana(ancho: int, alto: int, tw: int, th: int, cx: float, cy: float, escala: float):
    escala = max(escala, 1.0)
    if ancho / alto > tw / th:
        base_h = float(alto)
        base_w = alto * tw / th
    else:
        base_w = float(ancho)
        base_h = ancho * th / tw
    cw = max(2, int(round(base_w / escala)))
    ch = max(2, int(round(base_h / escala)))
    cw = min(cw, ancho)
    ch = min(ch, alto)
    x = int(round(cx - cw / 2))
    y = int(round(cy - ch / 2))
    x = max(0, min(x, ancho - cw))
    y = max(0, min(y, alto - ch))
    return x, y, cw, ch


def _escala_zoom(t_local: float, zooms: list[dict] | None) -> float:
    escala = 1.0
    for z in zooms or []:
        t0 = float(z["t"])
        dur = float(z["dur"])
        if t0 <= t_local < t0 + dur:
            escala = max(escala, float(z["escala"]))
    return escala


def escribir_desde_python(
    src: Path,
    dst: Path,
    inn: float,
    out: float,
    velocidad: float,
    tw: int,
    th: int,
    fps: int,
    cx_fn,
    zooms: list[dict] | None,
) -> None:
    """Recorte cuadro a cuadro. cx_fn(t_fuente) devuelve el centro en píxeles, o None."""
    import cv2

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise SystemExit(f"OpenCV no pudo abrir {src}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or fps
    ancho = int(cap.get(3))
    alto = int(cap.get(4))
    inicio = int(round(inn * src_fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, inicio)
    n_out = max(1, int(round((out - inn) / velocidad * fps)))
    dst.parent.mkdir(parents=True, exist_ok=True)
    crudo = dst.with_suffix(".video.mov")
    ff = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{tw}x{th}",
            "-r",
            str(fps),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "14",
            "-pix_fmt",
            "yuv420p",
            str(crudo),
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert ff.stdin is not None
    loaded = -1
    frame = None
    try:
        for k in range(n_out):
            rel = int(round(k * velocidad * src_fps / fps))
            while loaded < rel:
                ok, frame = cap.read()
                if not ok:
                    break
                loaded += 1
            if frame is None:
                raise SystemExit(f"Sin cuadros en {src} desde {inn}s.")
            t_fuente = inn + (k / fps) * velocidad
            t_local = k / fps
            cx = cx_fn(t_fuente) if cx_fn else ancho / 2
            if cx is None:
                cx = ancho / 2
            escala = _escala_zoom(t_local, zooms)
            x, y, cw, ch = _ventana(ancho, alto, tw, th, float(cx), alto / 2, escala)
            recorte = frame[y : y + ch, x : x + cw]
            pintado = cv2.resize(recorte, (tw, th), interpolation=cv2.INTER_AREA)
            ff.stdin.write(np.ascontiguousarray(pintado).tobytes())
    except BrokenPipeError:
        err = ff.stderr.read().decode("utf-8", errors="replace") if ff.stderr else ""
        raise SystemExit(f"ffmpeg cortó el tubo de video.\n{err[-2000:]}")
    finally:
        cap.release()
        ff.stdin.close()
    err = ff.stderr.read().decode("utf-8", errors="replace") if ff.stderr else ""
    if ff.wait() != 0:
        raise SystemExit(f"ffmpeg no pudo codificar el tramo.\n{err[-2000:]}")
    _mux_audio(src, crudo, dst, inn, out, velocidad)
    crudo.unlink(missing_ok=True)


def _mux_audio(src: Path, video: Path, dst: Path, inn: float, out: float, velocidad: float) -> None:
    # -ss/-to después de -i: el corte cae en el tiempo pedido, no en el keyframe previo.
    # La guía los pone como opciones de entrada; el filtro de adentro es el mismo.
    audio = dst.with_suffix(".audio.wav")
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-ss",
            f"{inn:.3f}",
            "-to",
            f"{out:.3f}",
            "-vn",
            "-af",
            _atempo(velocidad),
            "-ar",
            "48000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(audio),
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-c:v",
            "copy",
            "-c:a",
            "pcm_s16le",
            "-shortest",
            str(dst),
        ]
    )
    audio.unlink(missing_ok=True)


def _filtro_color(guion: dict) -> list[str]:
    color = guion.get("color") or {}
    partes = []
    if color.get("eq"):
        partes.append(f"eq={color['eq']}")
    if color.get("lut"):
        partes.append(f"lut3d={color['lut']}")
    return partes


def _crop_centro(tw: int, th: int) -> str:
    # Aspecto de salida. En horizontal → vertical coincide con crop=ih*9/16:ih:(iw-oh)/2:0
    # de la guía, porque el alto del recorte es el alto del cuadro.
    return (
        f"crop='trunc(min(iw,ih*{tw}/{th})/2)*2':'trunc(min(ih,iw*{th}/{tw})/2)*2':"
        f"'(iw-ow)/2':'(ih-oh)/2'"
    )


def _tramo_ffmpeg(
    src: Path,
    dst: Path,
    inn: float,
    out: float,
    velocidad: float,
    tw: int,
    th: int,
    fps: int,
    extra_vf: list[str],
) -> None:
    vf = ",".join(
        [
            f"setpts=PTS/{velocidad:.6f}",
            _crop_centro(tw, th),
            *extra_vf,
            f"scale={tw}:{th}",
            f"fps={fps}",
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-ss",
            f"{inn:.3f}",
            "-to",
            f"{out:.3f}",
            "-vf",
            vf,
            "-af",
            _atempo(velocidad),
            "-c:v",
            "libx264",
            "-crf",
            "14",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "48000",
            str(dst),
        ]
    )


def _placa(dst: Path, color: str, tw: int, th: int, fps: int, dur: float) -> None:
    c = color.replace("#", "0x")
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={c}:s={tw}x{th}:r={fps}:d={dur:.3f}",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=mono:sample_rate=48000",
            "-shortest",
            "-c:v",
            "libx264",
            "-crf",
            "14",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "48000",
            str(dst),
        ]
    )


def _ruta_trabajo(proyecto: Path, guion: dict, fuente: str) -> Path:
    rel = (guion.get("fuentes") or {}).get(fuente)
    if not rel:
        raise SystemExit(f"La fuente {fuente} no está en guion.fuentes.")
    stem = Path(rel).stem
    trabajo = proyecto / "trabajo" / f"{stem}.mov"
    if not trabajo.exists():
        raise SystemExit(f"Falta {trabajo}. Normalizá {rel} antes de construir la edición.")
    return trabajo


def _cx_de(cara_json: Path):
    if not cara_json.exists():
        raise SystemExit(f"Falta {cara_json}. Corré analizar antes de un encuadre de cara.")
    cara = json.loads(cara_json.read_text(encoding="utf-8"))
    if not cara:
        return lambda _t: None
    ts = np.array([c["t"] for c in cara], dtype=float)
    cx = np.array([c["cx"] for c in cara], dtype=float)

    def fn(t: float) -> float:
        return float(np.interp(t, ts, cx))

    return fn


def construir(proyecto: Path) -> Path:
    guion = cargar(proyecto / "guion.json")
    edicion = guion.get("edicion") or []
    if not edicion:
        raise SystemExit("El guion no tiene edicion. No hay capa de video que construir.")
    fmt = guion["formato"]
    tw, th, fps = int(fmt["w"]), int(fmt["h"]), int(fmt["fps"])
    tramos_dir = proyecto / "tramos"
    tramos_dir.mkdir(parents=True, exist_ok=True)
    color_vf = _filtro_color(guion)
    piezas: list[Path] = []
    for i, e in enumerate(edicion, start=1):
        dst = tramos_dir / f"{i:02d}.mov"
        velocidad = float(e.get("velocidad", 1.0))
        inn, out = float(e["in"]), float(e["out"])
        if e.get("fuente") == "color":
            tono = e.get("color") or "#000000"
            _placa(dst, tono, tw, th, fps, (out - inn) / velocidad)
            piezas.append(dst)
            continue
        src = _ruta_trabajo(proyecto, guion, e["fuente"])
        encuadre = e.get("encuadre", "centro")
        zooms = e.get("zoom") or []
        if encuadre not in ("centro", "cara"):
            raise SystemExit(f"Encuadre desconocido: {encuadre}. Usá centro o cara.")
        # Zoom o cara: el bucle de Python. El encuadre fijo va por ffmpeg, como la guía.
        if encuadre == "cara" or zooms:
            stem = Path(guion["fuentes"][e["fuente"]]).stem
            cx_fn = _cx_de(proyecto / "analisis" / f"{stem}.cara.json") if encuadre == "cara" else None
            escribir_desde_python(src, dst, inn, out, velocidad, tw, th, fps, cx_fn, zooms)
            if color_vf:
                pintado = dst.with_suffix(".color.mov")
                run(
                    [
                        "ffmpeg",
                        "-y",
                        "-loglevel",
                        "error",
                        "-i",
                        str(dst),
                        "-vf",
                        ",".join(color_vf),
                        "-c:v",
                        "libx264",
                        "-crf",
                        "14",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "copy",
                        str(pintado),
                    ]
                )
                pintado.replace(dst)
        else:
            _tramo_ffmpeg(src, dst, inn, out, velocidad, tw, th, fps, color_vf)
        piezas.append(dst)
        print(f"tramo {i:02d}  {e.get('fuente')}  {inn:.2f}-{out:.2f}")

    lista = tramos_dir / "tramos.txt"
    # Rutas absolutas: el concat de la guía usa el nombre relativo y asume el cwd.
    # Acá no dependemos del directorio desde el que se corre el comando.
    lista.write_text("".join(f"file '{p.resolve()}'\n" for p in piezas), encoding="utf-8")
    salida = proyecto / "trabajo" / "capa_video.mov"
    salida.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lista),
            "-c:v",
            "libx264",
            "-crf",
            "14",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "48000",
            str(salida),
        ]
    )
    tramos, total = construir_mapa(edicion)
    palabras: dict[str, list] = {}
    for fuente, rel in (guion.get("fuentes") or {}).items():
        pj = proyecto / "analisis" / f"{Path(rel).stem}.palabras.json"
        if pj.exists():
            palabras[fuente] = json.loads(pj.read_text(encoding="utf-8"))
    if palabras:
        final = palabras_en_final(tramos, palabras)
        (proyecto / "analisis").mkdir(parents=True, exist_ok=True)
        (proyecto / "analisis" / "final.palabras.json").write_text(
            json.dumps(final, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
    (proyecto / "analisis").mkdir(parents=True, exist_ok=True)
    (proyecto / "analisis" / "mapa.json").write_text(
        json.dumps({"tramos": tramos, "duracion": total}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"capa de video  {salida}  ({total:.2f}s)")
    return salida


def _proponer_cmd(proyecto: Path, fuente: str) -> None:
    guion = cargar(proyecto / "guion.json")
    rel = (guion.get("fuentes") or {}).get(fuente)
    if not rel:
        raise SystemExit(f"La fuente {fuente} no está en el guion.")
    stem = Path(rel).stem
    palabras_path = proyecto / "analisis" / f"{stem}.palabras.json"
    sil_path = proyecto / "analisis" / f"{stem}.silencios.json"
    if not palabras_path.exists() or not sil_path.exists():
        raise SystemExit("Falta el análisis de esa fuente. Corré analizar.py primero.")
    palabras = json.loads(palabras_path.read_text(encoding="utf-8"))
    silencios = json.loads(sil_path.read_text(encoding="utf-8"))
    if not palabras:
        raise SystemExit("La transcripción está vacía. No armo una propuesta.")
    duracion = max(float(p["b"]) for p in palabras)
    edicion = proponer_tramos(palabras, silencios, duracion, fuente)
    destino = proyecto / "analisis" / "edicion.propuesta.json"
    destino.write_text(
        json.dumps(
            {
                "estado": "propuesta",
                "requiere_aprobacion": True,
                "nota": "Una persona tiene que aprobar esta lista antes de copiarla al guion. El encuadre por defecto es centro.",
                "aire_s": AIRE,
                "edicion": edicion,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"propuesta  {destino}  ({len(edicion)} tramos)")
    print("No la copié al guion. La tiene que aprobar una persona.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Proponer o construir la capa de video.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("proponer", help="Jump cuts a partir del análisis. No toca el guion.")
    p.add_argument("--proyecto", type=Path, default=Path("."))
    p.add_argument("--fuente", required=True, help="Id de la fuente en el guion, por ejemplo A.")
    c = sub.add_parser("construir", help="Construir trabajo/capa_video.mov desde guion.edicion.")
    c.add_argument("--proyecto", type=Path, default=Path("."))
    args = ap.parse_args(argv)
    proyecto = args.proyecto.resolve()
    if args.cmd == "proponer":
        _proponer_cmd(proyecto, args.fuente)
    else:
        construir(proyecto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
