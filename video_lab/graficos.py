"""Render de la capa gráfica con Playwright. Sección 10.

Cada cuadro llama render(t) y se manda a ffmpeg. No hay reloj de pared.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from video_lab.guion import (
    bloques_de_subtitulos,
    cargar,
    duracion_de,
    escenas_resueltas,
    tokens_de,
)
from video_lab.sync import warp_de
from video_lab.zonas import zona_para


def escribir_css_fuentes(proyecto: Path, tokens: dict) -> str:
    fonts = tokens.get("font") or {}
    familia = fonts.get("texto") or "Noto Sans"
    directorio = proyecto / "brand" / "fonts"
    if not (directorio / "texto.ttf").exists():
        raise SystemExit(
            "Falta brand/fonts/texto.ttf. Corré bash scripts/setup.sh "
            "o copiá ahí la fuente de la marca."
        )
    caras = []
    vistos = set()
    for rol, archivo in (("texto", "texto.ttf"), ("titulo", "titulo.ttf"), ("mono", "mono.ttf")):
        path = directorio / archivo
        if not path.exists():
            path = directorio / "texto.ttf"
        nombre = fonts.get(rol) or familia
        clave = (nombre, path.name)
        if clave in vistos:
            continue
        vistos.add(clave)
        caras.append(
            "@font-face {"
            f' font-family: "{nombre}";'
            f' src: url("../brand/fonts/{path.name}") format("truetype");'
            " font-weight: 100 900;"
            " font-style: normal; }"
        )
    css = proyecto / "capas" / "fuentes.css"
    css.parent.mkdir(parents=True, exist_ok=True)
    css.write_text("\n".join(caras) + "\n", encoding="utf-8")
    return familia


def _palabras(proyecto: Path, guion: dict) -> tuple[list, list]:
    sub = guion.get("subtitulos") or {}
    if not sub.get("activar"):
        return [], []
    marca = proyecto / "analisis" / "transcripcion.revisada"
    texto = marca.read_text(encoding="utf-8").strip() if marca.exists() else ""
    if texto != "revisada":
        raise SystemExit(
            "Los subtítulos están activos y nadie marcó la transcripción como revisada.\n"
            "Una persona tiene que leer analisis/*.palabras.json y, si cierra, escribir\n"
            "la palabra revisada en analisis/transcripcion.revisada.\n"
            "No crees ese archivo vos: la guía pide revisión humana."
        )
    ruta = proyecto / "analisis" / "final.palabras.json"
    if not ruta.exists():
        raise SystemExit(
            "Falta analisis/final.palabras.json. "
            "Construí la edición para reubicar las palabras en la línea de tiempo final."
        )
    palabras = json.loads(ruta.read_text(encoding="utf-8"))
    return palabras, bloques_de_subtitulos(palabras)


def _warp(proyecto: Path):
    ruta = proyecto / "analisis" / "warp.json"
    if not ruta.exists():
        return lambda t: t
    data = json.loads(ruta.read_text(encoding="utf-8"))
    return warp_de(data["R"], data["A"])[0]


def renderizar(
    proyecto: Path,
    salida: Path,
    con_alfa: bool,
    duracion: float | None = None,
) -> Path:
    guion = cargar(proyecto / "guion.json")
    if duracion is None:
        duracion = duracion_de(guion)
    fmt = guion["formato"]
    w, h, fps = int(fmt["w"]), int(fmt["h"]), int(fmt["fps"])
    if w % 2 or h % 2:
        raise SystemExit(f"La resolución {w}×{h} tiene que ser par para yuv420.")
    tokens = tokens_de(guion, proyecto)
    familia = escribir_css_fuentes(proyecto, tokens)
    palabras, bloques = _palabras(proyecto, guion)
    warp = _warp(proyecto)
    zona = zona_para(w, h)
    payload = {
        "formato": {"w": w, "h": h, "fps": fps, "duracion": duracion},
        "tokens": tokens,
        "escenas": escenas_resueltas(guion, duracion, proyecto),
        "zona": zona,
        "con_alfa": con_alfa,
        "subtitulos": guion.get("subtitulos") or {"activar": False},
        "palabras": palabras,
        "bloques": bloques,
        "logo": (proyecto / "brand" / "logo.png").exists(),
        "familia": familia,
        "duracion": duracion,
    }
    salida.parent.mkdir(parents=True, exist_ok=True)
    n = int(round(fps * duracion))
    if n < 1:
        raise SystemExit("La duración no alcanza para un cuadro.")
    print(f"render gráfico  {w}×{h}  {fps} fps  {n} cuadros  alfa={con_alfa}")
    asyncio.run(_cuadros(proyecto, salida, payload, warp, n, fps, con_alfa))
    print(f"capa gráfica  {salida}")
    return salida


async def _cuadros(proyecto, salida, payload, warp, n, fps, con_alfa) -> None:
    from playwright.async_api import async_playwright

    html = (proyecto / "capas" / "graficos.html").resolve()
    if not html.exists():
        raise SystemExit(f"No está {html}. Copiá templates/proyecto/capas.")
    codec_in = "png" if con_alfa else "mjpeg"
    if con_alfa:
        cola = ["-c:v", "qtrle", "-pix_fmt", "argb", str(salida)]
    else:
        cola = [
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-preset",
            "slow",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(salida),
        ]
    log = salida.with_suffix(".ffmpeg.log")
    log_f = open(log, "w", encoding="utf-8")
    ff = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "image2pipe",
            "-framerate",
            str(fps),
            "-c:v",
            codec_in,
            "-i",
            "-",
            "-r",
            str(fps),
            *cola,
        ],
        stdin=subprocess.PIPE,
        stderr=log_f,
    )
    assert ff.stdin is not None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=[
                    "--disable-gpu",
                    "--font-render-hinting=none",
                    "--disable-lcd-text",
                    "--force-device-scale-factor=1",
                    "--hide-scrollbars",
                ]
            )
            page = await browser.new_page(
                viewport={"width": payload["formato"]["w"], "height": payload["formato"]["h"]},
                device_scale_factor=1,
            )
            await page.goto(html.as_uri(), wait_until="load")
            await page.evaluate("(d) => { window.VIDEO_LAB = d }", payload)
            ok = await page.evaluate(
                """async (fam) => {
                    await document.fonts.ready;
                    return document.fonts.check('800 64px "' + fam + '"');
                }""",
                payload["familia"],
            )
            if not ok:
                raise SystemExit(
                    f'La fuente "{payload["familia"]}" no cargó. '
                    "Revisá brand/fonts/texto.ttf y font.texto en los tokens."
                )
            # La guía espera 400 ms después de document.fonts.ready, antes del primer cuadro.
            await page.wait_for_timeout(400)
            for i in range(n):
                t = float(warp(i / fps))
                await page.evaluate("(t) => render(t)", t)
                if con_alfa:
                    ff.stdin.write(await page.screenshot(type="png", omit_background=True))
                else:
                    ff.stdin.write(await page.screenshot(type="jpeg", quality=95))
                if i % fps == 0:
                    print(f"  cuadro {i}/{n}", file=sys.stderr)
            await browser.close()
    except BrokenPipeError:
        cola_log = log.read_text(encoding="utf-8")[-2000:] if log.exists() else ""
        raise SystemExit(f"ffmpeg cortó el tubo de la capa gráfica.\n{cola_log}")
    finally:
        ff.stdin.close()
        log_f.close()
    if ff.wait() != 0:
        cola_log = log.read_text(encoding="utf-8")[-2000:] if log.exists() else ""
        raise SystemExit(f"ffmpeg no pudo cerrar la capa gráfica.\n{cola_log}")
    log.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Renderizar capas/graficos.html.")
    ap.add_argument("--proyecto", type=Path, default=Path("."))
    ap.add_argument("--salida", type=Path, default=None)
    ap.add_argument("--alfa", action="store_true", help="QuickTime Animation con transparencia.")
    ap.add_argument("--duracion", type=float, default=None)
    args = ap.parse_args(argv)
    proyecto = args.proyecto.resolve()
    if args.salida:
        salida = args.salida if args.salida.is_absolute() else proyecto / args.salida
    elif args.alfa:
        salida = proyecto / "trabajo" / "capa_graficos.mov"
    else:
        salida = proyecto / "trabajo" / "graficos.mp4"
    renderizar(proyecto, salida, con_alfa=args.alfa, duracion=args.duracion)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
