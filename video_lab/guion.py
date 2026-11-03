"""Lectura del guion y tiempos relativos al final. Sección 5."""

from __future__ import annotations

import json
import re
from pathlib import Path

from video_lab.mapa import construir_mapa

_FIN = re.compile(r"^fin(?:\s*([+-])\s*([0-9]*\.?[0-9]+))?$")


def cargar(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"No está el guion: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if "formato" not in data:
        raise SystemExit("Al guion le falta formato.")
    for clave in ("w", "h", "fps", "duracion"):
        if clave not in data["formato"]:
            raise SystemExit(f"Al formato le falta {clave}.")
    return data


def duracion_de(guion: dict) -> float:
    valor = guion["formato"]["duracion"]
    if valor == "auto":
        edicion = guion.get("edicion") or []
        if not edicion:
            raise SystemExit(
                'duracion es "auto" y no hay tramos en edicion. '
                "En un video solo gráfico escribí un número."
            )
        _, total = construir_mapa(edicion)
        return total
    return float(valor)


def resolver_tiempo(valor, duracion: float) -> float:
    """Acepta un número, "fin" o "fin-3.5" / "fin+1"."""
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    texto = str(valor).strip().replace(" ", "")
    if texto == "zoom":
        raise SystemExit('resolver_tiempo no resuelve "zoom"; eso es un evento de sonido.')
    coincidencia = _FIN.match(texto)
    if coincidencia:
        if not coincidencia.group(1):
            return float(duracion)
        signo = 1.0 if coincidencia.group(1) == "+" else -1.0
        return float(duracion) + signo * float(coincidencia.group(2))
    return float(texto)


def escenas_resueltas(guion: dict, duracion: float, proyecto: Path) -> list[dict]:
    """Tiempos numéricos y, si una escena apunta a un JSON, el objeto ya cargado."""
    salida = []
    for cruda in guion.get("escenas") or []:
        escena = dict(cruda)
        escena["desde"] = resolver_tiempo(cruda["desde"], duracion)
        escena["hasta"] = resolver_tiempo(cruda["hasta"], duracion)
        if escena["hasta"] <= escena["desde"]:
            raise SystemExit(f"La escena {escena.get('id')} termina antes de empezar.")
        datos = escena.get("datos")
        if isinstance(datos, str):
            ruta = (proyecto / datos).resolve()
            if not ruta.exists():
                raise SystemExit(f"La escena {escena.get('id')} apunta a {datos} y no está.")
            escena["datos"] = json.loads(ruta.read_text(encoding="utf-8"))
        salida.append(escena)
    return salida


def bloques_de_subtitulos(palabras: list[dict], minimo: int = 2, maximo: int = 4) -> list[dict]:
    """Bloques de 2 a 4 palabras. No corta una frase si el signo llega antes.

    La regla está en la sección 8. El snippet de la guía agrupa de a 3;
    acá se sigue la regla (2 a 4, sin cortar la frase) para que el .srt
    y la capa gráfica usen los mismos bloques.
    """
    bloques: list[list[dict]] = []
    actual: list[dict] = []
    for indice, palabra in enumerate(palabras):
        actual.append({**palabra, "i": indice})
        cierra = bool(re.search(r"[.!?…:]$", str(palabra["w"]).strip()))
        if len(actual) >= maximo or (len(actual) >= minimo and cierra):
            bloques.append(actual)
            actual = []
    if actual:
        if len(actual) == 1 and bloques and len(bloques[-1]) < maximo:
            bloques[-1].extend(actual)
        else:
            bloques.append(actual)
    resultado = []
    for grupo in bloques:
        resultado.append(
            {
                "i0": grupo[0]["i"],
                "i1": grupo[-1]["i"],
                "palabras": [{"w": p["w"], "a": p["a"], "b": p["b"]} for p in grupo],
            }
        )
    return resultado


def tokens_de(guion: dict, proyecto: Path) -> dict:
    rel = guion.get("marca") or "brand/tokens.json"
    ruta = proyecto / rel
    if not ruta.exists():
        raise SystemExit(f"No está el kit de marca: {ruta}")
    return json.loads(ruta.read_text(encoding="utf-8"))
