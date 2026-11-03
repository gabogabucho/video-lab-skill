"""Render, efectos, mezcla y las cuatro entregas. Secciones 10 a 12.

`entregar.py` no está nombrado en la guía: junta graficos, sfx, componer y qa
para no dejar el orden a la memoria. No elige el guion ni la marca.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from video_lab.audio import resolver_voz
from video_lab.editar import _placa, construir
from video_lab.ff import run
from video_lab.graficos import renderizar
from video_lab.guion import bloques_de_subtitulos, cargar, duracion_de, tokens_de
from video_lab.paths import ROOT
from video_lab.qa import revisar
from video_lab.sfx import desde_guion


def _componer_sh(proyecto: Path) -> Path:
    local = proyecto / "scripts" / "componer.sh"
    if local.exists():
        return local
    skill = ROOT / "scripts" / "componer.sh"
    if skill.exists():
        return skill
    raise SystemExit("No está componer.sh.")


def _srt(palabras: list[dict], destino: Path) -> None:
    bloques = bloques_de_subtitulos(palabras)

    def ts(t: float) -> str:
        if t < 0:
            t = 0.0
        total_ms = int(round(t * 1000))
        h, rem = divmod(total_ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lineas = []
    for i, bloque in enumerate(bloques, start=1):
        palabras_b = bloque["palabras"]
        lineas.append(str(i))
        lineas.append(f"{ts(palabras_b[0]['a'])} --> {ts(palabras_b[-1]['b'])}")
        lineas.append(" ".join(p["w"] for p in palabras_b))
        lineas.append("")
    destino.write_text("\n".join(lineas), encoding="utf-8")
    print(f"srt      {destino}")


def entregar(proyecto: Path, salida: Path, fondo: bool, con_qa: bool) -> Path:
    guion_path = proyecto / "guion.json"
    guion = cargar(guion_path)
    duracion = duracion_de(guion)
    fmt = guion["formato"]
    w, h, fps = int(fmt["w"]), int(fmt["h"]), int(fmt["fps"])
    edicion = guion.get("edicion") or []
    trabajo = proyecto / "trabajo"
    out = proyecto / "out"
    trabajo.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    capa = trabajo / "capa_video.mov"
    if edicion:
        if not capa.exists() or capa.stat().st_mtime < guion_path.stat().st_mtime:
            construir(proyecto)
        video = capa
        alfa = True
    elif fondo:
        tokens = tokens_de(guion, proyecto)
        video = trabajo / "placa.mp4"
        _placa(video, tokens["color"]["fondo"], w, h, fps, duracion)
        alfa = True
        print(f"placa    {video}")
    else:
        video = None
        alfa = False

    graficos = trabajo / ("capa_graficos.mov" if alfa else "graficos.mp4")
    renderizar(proyecto, graficos, con_alfa=alfa, duracion=duracion)

    efectos = out / "efectos.wav"
    desde_guion(proyecto, efectos)
    voz = out / "voz.wav"
    resolver_voz(guion, proyecto, video, voz, duracion)

    salida.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["bash", str(_componer_sh(proyecto))]
    if alfa:
        cmd += [str(video), str(graficos), str(voz), str(efectos), str(salida), f"{duracion:.3f}"]
    else:
        cmd += ["--solo-grafico", str(graficos), str(voz), str(efectos), str(salida), f"{duracion:.3f}"]
    print("mezclando…")
    run(cmd)

    mudo = salida.with_name(salida.stem + "_sin_audio.mp4")
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(salida),
            "-an",
            "-c:v",
            "copy",
            "-movflags",
            "+faststart",
            str(mudo),
        ]
    )
    print(f"sin audio  {mudo}")
    print(f"efectos    {efectos}")

    if (guion.get("subtitulos") or {}).get("activar"):
        palabras = json_palabras(proyecto)
        _srt(palabras, salida.with_name("subtitulos.srt") if salida.parent == out else out / "subtitulos.srt")

    print(f"final    {salida}")
    if con_qa:
        revisar(salida, w, h, fps, duracion, out / "hoja.png")
    return salida


def json_palabras(proyecto: Path) -> list[dict]:
    import json

    ruta = proyecto / "analisis" / "final.palabras.json"
    if not ruta.exists():
        raise SystemExit("Subtítulos activos y falta analisis/final.palabras.json.")
    return json.loads(ruta.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render, mezcla y entregas de un proyecto.")
    ap.add_argument("--proyecto", type=Path, default=Path("."))
    ap.add_argument("--salida", type=Path, default=None)
    ap.add_argument(
        "--fondo",
        action="store_true",
        help="Sin edición: placa del color de marca y gráficos con alfa (flujo mixto).",
    )
    ap.add_argument("--sin-qa", action="store_true")
    args = ap.parse_args(argv)
    proyecto = args.proyecto.resolve()
    salida = args.salida or (proyecto / "out" / "final.mp4")
    if not salida.is_absolute():
        salida = proyecto / salida
    entregar(proyecto, salida, fondo=args.fondo, con_qa=not args.sin_qa)
    return 0


if __name__ == "__main__":
    sys.exit(main())
