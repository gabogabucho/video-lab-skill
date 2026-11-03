"""Mapa de tiempos entre el crudo y la línea de tiempo final. Sección 6.4."""

from __future__ import annotations


def construir_mapa(edicion: list[dict]) -> tuple[list[dict], float]:
    tramos: list[dict] = []
    t0 = 0.0
    for e in edicion:
        velocidad = float(e.get("velocidad", 1.0))
        if velocidad <= 0:
            raise SystemExit("La velocidad de un tramo tiene que ser mayor que 0.")
        dur = (float(e["out"]) - float(e["in"])) / velocidad
        if dur <= 0:
            raise SystemExit(f"Tramo con duración <= 0: {e}")
        tramos.append({**e, "t0": t0, "t1": t0 + dur, "velocidad": velocidad})
        t0 += dur
    return tramos, t0


def palabras_en_final(tramos: list[dict], palabras_por_fuente: dict) -> list[dict]:
    salida = []
    for tr in tramos:
        if tr.get("fuente") == "color":
            continue
        v = float(tr.get("velocidad", 1.0))
        palabras = palabras_por_fuente.get(tr["fuente"], [])
        for p in palabras:
            if p["a"] >= tr["in"] and p["b"] <= tr["out"]:
                salida.append(
                    {
                        "w": p["w"],
                        "a": tr["t0"] + (p["a"] - tr["in"]) / v,
                        "b": tr["t0"] + (p["b"] - tr["in"]) / v,
                    }
                )
    return salida
