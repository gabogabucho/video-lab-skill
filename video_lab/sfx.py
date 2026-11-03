"""Efectos sintetizados. Sección 11. Semilla fija, sin bancos de terceros."""

from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

from video_lab.guion import cargar, duracion_de, resolver_tiempo
from video_lab.mapa import construir_mapa

SR = 44100
rng = np.random.default_rng(11)


def t_(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.002, d=0.1):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)


def lp(x, c):
    y = np.zeros_like(x)
    s = 0.0
    c = np.broadcast_to(np.asarray(c, dtype=float), x.shape)
    for i in range(len(x)):
        s += c[i] * (x[i] - s)
        y[i] = s
    return y


def hp(x, c=0.2):
    return x - lp(x, c)


def sweep(f0, f1, d, k=1.0):
    t = t_(d)
    f = f0 + (f1 - f0) * (t / d) ** k
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def pop(f=520, d=0.09, drop=0.45):
    return sweep(f, f * drop, d, 0.5) * env(int(SR * d), 0.001, d / 4)


def click(d=0.012, b=0.6):
    n = int(SR * d)
    return hp(rng.standard_normal(n) * env(n, 0.0003, d / 5), b) * 0.9


def whoosh(d=0.35):
    n = int(SR * d)
    t = np.arange(n) / n
    return hp(lp(rng.standard_normal(n), 0.02 + 0.25 * t**1.5), 0.02) * np.sin(np.pi * t) ** 1.6 * 2.2


def impacto(d=0.9):
    n = int(SR * d)
    cuerpo = sweep(95, 38, d, 0.35) * env(n, 0.002, 0.28)
    ruido = lp(rng.standard_normal(n), 0.08) * env(n, 0.001, 0.05) * 1.6
    return np.tanh((cuerpo * 1.6 + ruido) * 1.4)


def thump(f=110, d=0.3):
    n = int(SR * d)
    return np.tanh(
        (
            sweep(f, f * 0.45, d, 0.4) * env(n, 0.001, 0.09) * 1.5
            + lp(rng.standard_normal(n), 0.15) * env(n, 0.0005, 0.02)
        )
        * 1.3
    )


def ding(f=1320, d=0.5):
    n = int(SR * d)
    t = t_(d)
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.01 * t) + 0.2 * np.sin(2 * np.pi * f * 3.02 * t)
    return s * env(n, 0.002, d / 4) * 0.6


TIPOS = {
    "pop": pop,
    "click": click,
    "whoosh": whoosh,
    "impacto": impacto,
    "thump": thump,
    "ding": ding,
}


def construir(eventos, duracion, a_tiempo_real, salida: Path) -> None:
    # La guía crea el rng al importar. Lo reiniciamos en cada archivo para que
    # el wav no dependa de cuántas veces se llamó antes en el mismo proceso.
    global rng
    rng = np.random.default_rng(11)
    buf = np.zeros(int(SR * duracion))
    for e in eventos:
        if e["tipo"] not in TIPOS:
            raise SystemExit(f"Efecto desconocido: {e['tipo']}. Usá {', '.join(TIPOS)}.")
        snd = TIPOS[e["tipo"]]()
        i = int(a_tiempo_real(e["t"]) * SR)
        if i >= len(buf) or i < 0:
            print(f"aviso: el efecto {e['tipo']} en t={e['t']} cae fuera de la duración", file=sys.stderr)
            continue
        j = min(len(buf), i + len(snd))
        buf[i:j] += snd[: j - i] * float(e["gain"])
    pk = np.max(np.abs(buf)) if len(buf) else 0
    if pk > 0.95:
        buf *= 0.95 / pk
    salida.parent.mkdir(parents=True, exist_ok=True)
    w = wave.open(str(salida), "w")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    w.close()


def _tiempo_de_evento(valor, duracion: float, tramos: list[dict]):
    if valor == "zoom":
        for tr in tramos:
            zooms = tr.get("zoom") or []
            if zooms:
                # Supuesto: zoom.t es segundos desde que empieza ese tramo.
                return float(tr["t0"]) + float(zooms[0]["t"])
        raise SystemExit('Hay un evento con t="zoom" y la edición no tiene zoom.')
    return resolver_tiempo(valor, duracion)


def desde_guion(proyecto: Path, salida: Path) -> None:
    guion = cargar(proyecto / "guion.json")
    duracion = duracion_de(guion)
    tramos, _ = construir_mapa(guion.get("edicion") or [])
    eventos = (guion.get("audio") or {}).get("eventos_sfx") or []
    musica = (guion.get("audio") or {}).get("musica")
    if musica:
        print(
            "La música queda afuera de la mezcla. Sumala después, 15 a 20 dB bajo la voz.",
            file=sys.stderr,
        )

    def a_tiempo_real(valor):
        return _tiempo_de_evento(valor, duracion, tramos)

    construir(eventos, duracion, a_tiempo_real, salida)
    print(f"efectos  {salida}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sintetizar los efectos del guion.")
    ap.add_argument("--proyecto", type=Path, default=Path("."))
    ap.add_argument("--salida", type=Path, default=None)
    args = ap.parse_args(argv)
    proyecto = args.proyecto.resolve()
    salida = args.salida or (proyecto / "out" / "efectos.wav")
    if not salida.is_absolute():
        salida = proyecto / salida
    desde_guion(proyecto, salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
