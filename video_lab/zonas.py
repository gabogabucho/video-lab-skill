"""Zonas seguras de la sección 4 y el drawbox de la hoja de contactos."""

from __future__ import annotations

# x0–x1, y0–y1 en píxeles de la resolución canónica.
ZONAS = {
    "9:16": {
        "w": 1080,
        "h": 1920,
        "x0": 80,
        "x1": 940,
        "y0": 150,
        "y1": 1480,
        "uso": "TikTok, Reels, Shorts, Historias",
    },
    "4:5": {
        "w": 1080,
        "h": 1350,
        "x0": 60,
        "x1": 1020,
        "y0": 60,
        "y1": 1290,
        "uso": "Feed de Instagram y Facebook",
    },
    "1:1": {
        "w": 1080,
        "h": 1080,
        "x0": 60,
        "x1": 1020,
        "y0": 60,
        "y1": 1020,
        "uso": "Feed, LinkedIn",
    },
    "16:9": {
        "w": 1920,
        "h": 1080,
        "x0": 96,
        "x1": 1824,
        "y0": 54,
        "y1": 1026,
        "uso": "YouTube, web",
    },
}


def zona_para(w: int, h: int) -> dict:
    """Escala la zona canónica si el video conserva el aspecto.

    Una pieza a mitad de resolución (el humo) usa la misma zona, a escala.
    """
    if w <= 0 or h <= 0:
        raise SystemExit(f"Resolución inválida: {w}x{h}")
    ratio = w / h
    mejor = None
    for nombre, z in ZONAS.items():
        if abs(ratio - (z["w"] / z["h"])) < 0.02:
            mejor = (nombre, z)
            break
    if mejor is None:
        conocidas = ", ".join(f"{k} ({v['w']}×{v['h']})" for k, v in ZONAS.items())
        raise SystemExit(
            f"No hay zona segura para {w}×{h}. Formatos de la guía: {conocidas}."
        )
    nombre, z = mejor
    sx = w / z["w"]
    sy = h / z["h"]
    return {
        "nombre": nombre,
        "x0": int(round(z["x0"] * sx)),
        "x1": int(round(z["x1"] * sx)),
        "y0": int(round(z["y0"] * sy)),
        "y1": int(round(z["y1"] * sy)),
        "w": w,
        "h": h,
    }


def drawbox_hoja(zona: dict, tw: int, th: int) -> tuple[int, int, int, int]:
    """Rectángulo de la zona segura sobre un cuadro ya escalado.

    Para 9:16 llevado a 270×480 da x=20, y=37, w=215, h=333, que es el
    drawbox de la guía. y trunca y el alto se mide hasta el borde inferior
    truncado, que es como salen 37 y 333 (150×0,25 = 37,5).
    """
    sx = tw / zona["w"]
    sy = th / zona["h"]
    x = int(zona["x0"] * sx)
    y = int(zona["y0"] * sy)
    bw = int(zona["x1"] * sx) - x
    bh = int(zona["y1"] * sy) - y
    return x, y, bw, bh
