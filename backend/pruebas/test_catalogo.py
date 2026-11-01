"""Pruebas de la lectura del catálogo."""

from pathlib import Path

import pytest

from app.config import obtener_configuracion
from app.extraccion.catalogo import ErrorCatalogo, leer_catalogo


def escribir(tmp_path: Path, contenido: str) -> Path:
    archivo = tmp_path / "catalogo.toml"
    archivo.write_text(contenido, encoding="utf-8")
    return archivo


def test_lee_productos_con_sus_identificadores_por_tienda(tmp_path: Path) -> None:
    archivo = escribir(
        tmp_path,
        '[[producto]]\nnombre = "Celular X 128 GB"\ncategoria = "tecnologia"\nmarca = "X"\n'
        '[producto.ids]\nmercadolibre = ["MCO1", "MCO2"]\n\n'
        '[[producto]]\nnombre = "Freidora Y"\ncategoria = "hogar"\n',
    )

    productos = leer_catalogo(archivo)

    assert [p.nombre for p in productos] == ["Celular X 128 GB", "Freidora Y"]
    assert productos[0].marca == "X"
    assert productos[0].ids == {"mercadolibre": ["MCO1", "MCO2"]}
    assert productos[1].ids == {}


def test_rechaza_productos_repetidos(tmp_path: Path) -> None:
    archivo = escribir(
        tmp_path,
        '[[producto]]\nnombre = "A"\ncategoria = "c"\n[[producto]]\nnombre = "A"\ncategoria = "c"\n',
    )

    with pytest.raises(ErrorCatalogo, match="repetido"):
        leer_catalogo(archivo)


def test_rechaza_productos_sin_categoria(tmp_path: Path) -> None:
    archivo = escribir(tmp_path, '[[producto]]\nnombre = "A"\n')

    with pytest.raises(ErrorCatalogo, match="#1"):
        leer_catalogo(archivo)


def test_el_catalogo_del_proyecto_se_puede_leer() -> None:
    assert leer_catalogo(obtener_configuracion().catalogo_path)
