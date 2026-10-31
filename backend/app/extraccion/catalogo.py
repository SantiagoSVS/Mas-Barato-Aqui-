"""Lectura del catálogo inicial (backend/catalogo.toml)."""

import tomllib
from pathlib import Path


def leer_terminos(ruta: Path) -> list[str]:
    """Devuelve todos los términos del catálogo, sin repetidos y en el orden del archivo."""
    with ruta.open("rb") as archivo:
        datos = tomllib.load(archivo)

    terminos: list[str] = []
    for categoria in datos.get("categoria", []):
        for termino in categoria.get("terminos", []):
            termino = termino.strip()
            if termino and termino not in terminos:
                terminos.append(termino)
    return terminos
