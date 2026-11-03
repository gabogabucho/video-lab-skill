"""Mapa de sincronía con una voz externa. Sección 9."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def validar_anclas(reales: list[float], animacion: list[float]) -> None:
    if len(reales) != len(animacion) or len(reales) < 2:
        raise SystemExit("Hacen falta las mismas anclas en R y en A, al menos dos.")
    for i in range(1, len(reales)):
        dr = float(reales[i]) - float(reales[i - 1])
        da = float(animacion[i]) - float(animacion[i - 1])
        if dr <= 0 or da <= 0:
            raise SystemExit("Las anclas tienen que ser estrictamente crecientes.")
        # Cuánto se estira el tramo respecto del original, en cualquier sentido.
        factor = max(dr / da, da / dr)
        if factor > 3.0 + 1e-6:
            raise SystemExit(
                f"El tramo {i} queda a {factor:.2f}× (más de 3). Mové un ancla."
            )


def warp_de(reales: list[float], animacion: list[float]):
    validar_anclas(reales, animacion)
    r = np.asarray(reales, dtype=float)
    a = np.asarray(animacion, dtype=float)
    warp = lambda t: float(np.interp(t, r, a))  # tiempo real → animación
    warp_inv = lambda t: float(np.interp(t, a, r))  # animación → tiempo real
    return warp, warp_inv


def cargar_anclas(path: Path) -> tuple[list[float], list[float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "R" not in data or "A" not in data:
        raise SystemExit(f"{path} tiene que tener las listas R y A.")
    return list(data["R"]), list(data["A"])


def guardar(proyecto: Path, reales: list[float], animacion: list[float]) -> Path:
    validar_anclas(reales, animacion)
    destino = proyecto / "analisis" / "warp.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({"R": reales, "A": animacion}, indent=2) + "\n",
        encoding="utf-8",
    )
    return destino


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validar anclas y escribir analisis/warp.json.")
    ap.add_argument("anclas", type=Path, help="JSON con R (audio real) y A (animación).")
    ap.add_argument("--proyecto", type=Path, default=Path("."))
    args = ap.parse_args(argv)
    proyecto = args.proyecto.resolve()
    ruta = args.anclas if args.anclas.is_absolute() else proyecto / args.anclas
    reales, animacion = cargar_anclas(ruta)
    destino = guardar(proyecto, reales, animacion)
    print(f"warp  {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
