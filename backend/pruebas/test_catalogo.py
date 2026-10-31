"""Pruebas de la lectura del catálogo."""

from pathlib import Path

from app.config import obtener_configuracion
from app.extraccion.catalogo import leer_terminos


def test_lee_terminos_de_todas_las_categorias_sin_repetidos(tmp_path: Path) -> None:
    archivo = tmp_path / "catalogo.toml"
    archivo.write_text(
        '[[categoria]]\nnombre = "a"\nterminos = ["celular", " portátil "]\n'
        '[[categoria]]\nnombre = "b"\nterminos = ["celular", "freidora", ""]\n',
        encoding="utf-8",
    )

    assert leer_terminos(archivo) == ["celular", "portátil", "freidora"]


def test_el_catalogo_del_proyecto_se_puede_leer() -> None:
    assert leer_terminos(obtener_configuracion().catalogo_path)
