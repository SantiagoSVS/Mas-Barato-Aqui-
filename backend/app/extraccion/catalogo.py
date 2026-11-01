"""Lectura del catálogo inicial (backend/catalogo.toml)."""

import tomllib
from pathlib import Path

from pydantic import ValidationError

from app.extraccion.tipos import ProductoCatalogo


class ErrorCatalogo(ValueError):
    """El archivo del catálogo tiene un error; se informa en qué producto."""


def leer_catalogo(ruta: Path) -> list[ProductoCatalogo]:
    """Devuelve los productos del catálogo en el orden del archivo.

    Rechaza el archivo completo si un producto está incompleto o si dos tienen el mismo
    nombre: es mejor que el worker no arranque a que capture un catálogo mal escrito.
    """
    with ruta.open("rb") as archivo:
        datos = tomllib.load(archivo)

    productos: list[ProductoCatalogo] = []
    nombres: set[str] = set()
    for posicion, entrada in enumerate(datos.get("producto", []), start=1):
        try:
            producto = ProductoCatalogo(**entrada)
        except (TypeError, ValidationError) as error:
            raise ErrorCatalogo(f"Producto #{posicion} del catálogo no es válido: {error}") from error
        if producto.nombre in nombres:
            raise ErrorCatalogo(f"El producto {producto.nombre!r} está repetido en el catálogo")
        nombres.add(producto.nombre)
        productos.append(producto)
    return productos
