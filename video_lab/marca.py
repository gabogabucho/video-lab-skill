"""Kit de marca: verificar fuentes y tokens, recortar un logo. Sección 3.

No inventa colores. `desde-css` solo imprime lo que encuentra.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

from video_lab.paths import CARACTERES

COLORES = ("fondo", "superficie", "texto", "primario", "acento", "suave", "linea")
_CSS_HREF = re.compile(r'href="([^"]*\.css[^"]*)"')
_CSS_VAR = re.compile(r"--[a-zA-Z0-9-]+:\s*#[0-9a-fA-F]{3,8}")
_CSS_FONT = re.compile(r"url\([^)]*\.(?:woff2?|ttf)[^)]*\)")


def cmap_de(path: Path) -> dict:
    from fontTools.ttLib import TTFont

    return TTFont(path).getBestCmap() or {}


def faltantes(path: Path, caracteres: str = CARACTERES) -> list[str]:
    cmap = cmap_de(path)
    return [c for c in caracteres if ord(c) not in cmap]


def verificar_fuente(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"No está la fuente: {path}")
    faltan = faltantes(path)
    if faltan:
        raise SystemExit(f"La fuente no tiene: {faltan}")


def verificar_tokens(path: Path) -> None:
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    color = data.get("color") or {}
    for clave in COLORES:
        if clave not in color:
            raise SystemExit(f"A brand/tokens.json le falta color.{clave}")
    if "texto" not in (data.get("font") or {}):
        raise SystemExit("A brand/tokens.json le falta font.texto")
    pantalla = data.get("texto_en_pantalla") or {}
    for clave in ("titulo", "hook", "subtitulo"):
        if clave not in pantalla:
            raise SystemExit(f"A brand/tokens.json le falta texto_en_pantalla.{clave}")
    if "radio" not in data:
        raise SystemExit("A brand/tokens.json le falta radio")


def verificar_proyecto(proyecto: Path) -> None:
    tokens = proyecto / "brand" / "tokens.json"
    verificar_tokens(tokens)
    fuentes = sorted((proyecto / "brand" / "fonts").glob("*.ttf"))
    fuentes += sorted((proyecto / "brand" / "fonts").glob("*.woff"))
    fuentes += sorted((proyecto / "brand" / "fonts").glob("*.woff2"))
    if not fuentes:
        raise SystemExit(
            "No hay fuentes en brand/fonts. Corré scripts/setup.sh "
            "o copiá la fuente de la marca."
        )
    for fuente in fuentes:
        verificar_fuente(fuente)
        print(f"fuente ok  {fuente.name}")
    logo = proyecto / "brand" / "logo.png"
    if logo.exists():
        _exigir_alfa(logo)
        print(f"logo ok    {logo.name}")
    else:
        print("logo       (no está brand/logo.png; el cierre lo va a omitir)")
    print(f"tokens ok  {tokens}")


def _exigir_alfa(path: Path) -> None:
    from PIL import Image

    im = Image.open(path)
    if im.mode != "RGBA":
        raise SystemExit(f"{path} no tiene canal alfa. Recortalo con: marca.py logo")
    alfa = im.getchannel("A")
    if alfa.getextrema()[0] == 255:
        raise SystemExit(f"{path} es opaco. El logo tiene que ser PNG transparente.")


def recortar_logo(src: Path, dst: Path, umbral: int = 245) -> None:
    """Si las cuatro esquinas son blancas, las vuelve transparentes y recorta."""
    from PIL import Image

    im = Image.open(src).convert("RGBA")
    px = im.load()
    w, h = im.size
    esquinas = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]

    def blanco(c: tuple) -> bool:
        return c[0] >= umbral and c[1] >= umbral and c[2] >= umbral

    if all(blanco(c) for c in esquinas):
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if r >= umbral and g >= umbral and b >= umbral:
                    px[x, y] = (r, g, b, 0)
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)


def logo_demo(dst: Path) -> None:
    """Marca inventada (Norte) para la plantilla y el humo. No es un cliente."""
    from PIL import Image, ImageDraw

    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((36, 36, 476, 476), radius=96, fill=(47, 75, 60, 255))
    d.ellipse((176, 156, 336, 316), fill=(242, 239, 233, 255))
    d.rounded_rectangle((156, 300, 356, 360), radius=24, fill=(192, 83, 47, 255))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)


def desde_css(url: str) -> None:
    """Imprime colores y fuentes encontradas. No escribe tokens.json."""
    cuerpo, tipo = _bajar(url, 2_000_000)
    texto = cuerpo.decode("utf-8", errors="replace")
    print(f"# origen {url}")
    if "text/html" in tipo or "<html" in texto[:500].lower() or "href=" in texto[:2000]:
        hrefs = _CSS_HREF.findall(texto)
        if not hrefs:
            print("# no encontré href a .css")
        for href in hrefs:
            print(f"css  {href}")
        return
    variables = _CSS_VAR.findall(texto)
    fuentes = _CSS_FONT.findall(texto)
    if not variables and not fuentes:
        print("# no encontré variables --* ni url() de fuentes")
    for v in variables:
        print(f"color  {v}")
    for f in fuentes:
        print(f"fuente  {f}")
    print("# Esto no se guardó. Los tokens los confirma una persona.")


def _bajar(url: str, tope: int) -> tuple[bytes, str]:
    if not url.startswith("https://") and not url.startswith("http://"):
        raise SystemExit("desde-css espera una URL http(s).")
    pedido = urllib.request.Request(url, headers={"User-Agent": "video-lab-skill"})
    with urllib.request.urlopen(pedido, timeout=30) as resp:
        tipo = resp.headers.get("Content-Type", "")
        data = resp.read(tope + 1)
    if len(data) > tope:
        raise SystemExit("La respuesta pasa de 2 MB. Bajá el CSS a mano.")
    return data, tipo


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verificar o inspeccionar un kit de marca.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verificar", help="Tokens, fuentes y logo de un proyecto.")
    v.add_argument("--proyecto", type=Path, default=Path("."))

    c = sub.add_parser("desde-css", help="Imprimir colores y fuentes de una URL. No escribe.")
    c.add_argument("url")

    logo = sub.add_parser("logo", help="Recortar un logo con fondo blanco a PNG transparente.")
    logo.add_argument("--entrada", type=Path, required=True)
    logo.add_argument("--salida", type=Path, required=True)

    demo = sub.add_parser("logo-demo", help="Escribir el logo inventado de la plantilla.")
    demo.add_argument("salida", type=Path)

    args = ap.parse_args(argv)
    if args.cmd == "verificar":
        verificar_proyecto(args.proyecto.resolve())
    elif args.cmd == "desde-css":
        desde_css(args.url)
    elif args.cmd == "logo":
        recortar_logo(args.entrada, args.salida)
        print(f"logo  {args.salida}")
    elif args.cmd == "logo-demo":
        logo_demo(args.salida)
        print(f"logo demo  {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
