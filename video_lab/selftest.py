"""Pruebas de las funciones puras de la guía y de dos tubos cortos de ffmpeg."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def test_mapa():
    from video_lab.mapa import construir_mapa, palabras_en_final

    edicion = [
        {"fuente": "A", "in": 3.2, "out": 7.85, "velocidad": 1.0},
        {"fuente": "B", "in": 0.0, "out": 2.1, "velocidad": 1.0},
        {"fuente": "A", "in": 12.4, "out": 18.9, "velocidad": 1.05},
    ]
    tramos, total = construir_mapa(edicion)
    assert abs(tramos[0]["t1"] - 4.65) < 1e-9
    assert abs(tramos[1]["t0"] - tramos[0]["t1"]) < 1e-9
    assert abs(total - (4.65 + 2.1 + (6.5 / 1.05))) < 1e-9
    palabras = palabras_en_final(
        tramos,
        {"A": [{"w": "hola", "a": 3.3, "b": 3.6}, {"w": "no", "a": 1.0, "b": 1.2}]},
    )
    assert len(palabras) == 1 and palabras[0]["w"] == "hola"
    assert abs(palabras[0]["a"] - 0.1) < 1e-9


def test_tiempos():
    from video_lab.guion import bloques_de_subtitulos, resolver_tiempo

    assert resolver_tiempo("fin-3.5", 10) == 6.5
    assert resolver_tiempo("fin", 10) == 10
    assert resolver_tiempo("fin+1", 10) == 11
    assert resolver_tiempo(1.25, 10) == 1.25
    bloques = bloques_de_subtitulos(
        [
            {"w": "Uno", "a": 0.0, "b": 0.2},
            {"w": "dos.", "a": 0.2, "b": 0.4},
            {"w": "Tres", "a": 0.5, "b": 0.7},
            {"w": "cuatro", "a": 0.7, "b": 0.9},
            {"w": "cinco", "a": 0.9, "b": 1.1},
            {"w": "seis!", "a": 1.1, "b": 1.3},
        ]
    )
    assert bloques[0]["palabras"][1]["w"] == "dos."
    assert all(2 <= len(b["palabras"]) <= 4 for b in bloques)


def test_warp():
    from video_lab.sync import validar_anclas

    validar_anclas([0, 3.08, 3.65, 7.15, 9.22, 11.0], [0, 2.0, 2.58, 5.0, 7.4, 8.78])
    try:
        validar_anclas([0, 1], [0, 4])
    except SystemExit:
        return
    raise AssertionError("un tramo a 4× tenía que rechazarse")


def test_zona():
    from video_lab.zonas import drawbox_hoja, zona_para

    zona = zona_para(1080, 1920)
    assert drawbox_hoja(zona, 270, 480) == (20, 37, 215, 333)
    media = zona_para(540, 960)
    assert (media["x0"], media["y0"], media["x1"], media["y1"]) == (40, 75, 470, 740)


def test_hdr_flag():
    from video_lab.normalizar import es_hdr

    assert es_hdr({"streams": [{"color_transfer": "smpte2084"}]})
    assert not es_hdr({"streams": [{"color_transfer": "bt709"}]})


def test_proponer():
    from video_lab.editar import proponer_tramos

    ed = proponer_tramos(
        [
            {"w": "hola", "a": 0.5, "b": 0.8},
            {"w": "eh", "a": 1.0, "b": 1.2},
            {"w": "mundo", "a": 1.3, "b": 1.7},
            {"w": "otra", "a": 3.2, "b": 3.6},
        ],
        [{"a": 2.0, "b": 3.0}],
        4.0,
        "A",
    )
    assert ed and all(e["encuadre"] == "centro" for e in ed)
    assert all(not (e["in"] <= 1.05 and e["out"] >= 1.15) for e in ed)
    assert all(not (e["in"] <= 2.4 <= e["out"]) for e in ed)
    assert abs(ed[0]["in"] - 0.42) < 0.021

    sea = proponer_tramos(
        [
            {"w": "mirá", "a": 0.2, "b": 0.5},
            {"w": "o", "a": 0.6, "b": 0.7},
            {"w": "sea", "a": 0.7, "b": 0.9},
            {"w": "esto", "a": 1.3, "b": 1.6},
        ],
        [],
        2.0,
        "A",
    )
    assert all(not (e["in"] <= 0.65 and e["out"] >= 0.85) for e in sea)


def test_sfx_determinista():
    from video_lab.sfx import construir

    eventos = [
        {"t": 0.1, "tipo": "pop", "gain": 0.4},
        {"t": 0.4, "tipo": "whoosh", "gain": 0.3},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.wav"
        b = Path(tmp) / "b.wav"
        construir(eventos, 1.0, lambda t: float(t), a)
        construir(list(reversed(eventos))[::-1], 1.0, lambda t: float(t), b)
        assert a.read_bytes() == b.read_bytes()
        assert a.stat().st_size > 1000


def test_logo():
    from PIL import Image

    from video_lab.marca import faltantes, recortar_logo
    from video_lab.paths import ruta_fuente

    fuente = ruta_fuente()
    if fuente.exists():
        assert faltantes(fuente) == []
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "blanco.png"
        dst = Path(tmp) / "logo.png"
        im = Image.new("RGB", (40, 30), (255, 255, 255))
        px = im.load()
        for y in range(10, 20):
            for x in range(8, 28):
                px[x, y] = (20, 40, 30)
        im.save(src)
        recortar_logo(src, dst)
        out = Image.open(dst)
        assert out.mode == "RGBA"
        assert out.size[0] < 40 and out.size[1] < 30
        assert out.getchannel("A").getextrema()[1] == 255


def test_placa_recorte_y_concat():
    from video_lab.editar import _placa, escribir_desde_python
    from video_lab.ff import run, streams

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        src = base / "src.mov"
        _placa(src, "#224433", 320, 180, 30, 0.4)

        def cx(t: float) -> float:
            return 160 + 30 * (t / 0.4)

        recorte = base / "recorte.mov"
        escribir_desde_python(
            src,
            recorte,
            0.0,
            0.3,
            1.0,
            180,
            320,
            30,
            cx,
            [{"t": 0.1, "escala": 1.25, "dur": 0.08}],
        )
        v = streams(recorte, "video")[0]
        assert int(v["width"]) == 180 and int(v["height"]) == 320
        assert streams(recorte, "audio")

        a, b = base / "a.mov", base / "b.mov"
        _placa(a, "#2f4b3c", 160, 288, 30, 0.2)
        _placa(b, "#c0532f", 160, 288, 30, 0.2)
        lista = base / "tramos.txt"
        lista.write_text(f"file '{a.resolve()}'\nfile '{b.resolve()}'\n", encoding="utf-8")
        out = base / "junto.mov"
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
                str(out),
            ]
        )
        dur = float(streams(out, "video")[0]["duration"])
        assert abs(dur - 0.4) < 0.15, dur


TESTS = [
    test_mapa,
    test_tiempos,
    test_warp,
    test_zona,
    test_hdr_flag,
    test_proponer,
    test_sfx_determinista,
    test_logo,
    test_placa_recorte_y_concat,
]


def main() -> int:
    fallos = 0
    for test in TESTS:
        try:
            test()
        except Exception as exc:
            fallos += 1
            print(f"FALLO  {test.__name__}: {exc}")
        else:
            print(f"ok     {test.__name__}")
    if fallos:
        print(f"{fallos} prueba(s) fallaron")
        return 1
    print("selftest listo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
