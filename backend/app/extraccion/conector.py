"""Interfaz común de los conectores (RNF-06: agregar una tienda = escribir un conector).

Cada tienda tiene una clase que hereda de Conector e implementa buscar() y actualizar().
El resto del sistema (worker, normalización, base de datos) solo conoce esta interfaz.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from app.extraccion.tipos import OfertaCapturada, ProductoCatalogo


class ErrorConector(Exception):
    """Falla al consultar una tienda: sitio caído, respuesta inesperada, acceso no permitido."""


class Conector(ABC):
    # Debe coincidir con plataforma.nombre en la base de datos
    nombre_plataforma: ClassVar[str]
    # Nombre de la tienda en la sección ids de cada producto de catalogo.toml
    clave_catalogo: ClassVar[str]

    @abstractmethod
    def buscar(self, producto: ProductoCatalogo) -> list[OfertaCapturada]:
        """Devuelve las ofertas de un producto del catálogo en esta tienda.

        Puede usar los identificadores de producto.ids[clave_catalogo] o buscar por nombre,
        según lo que permita la tienda. Lista vacía si la tienda no tiene el producto.
        """

    @abstractmethod
    def actualizar(self, url: str) -> OfertaCapturada | None:
        """Vuelve a consultar una oferta ya conocida. None si ya no existe."""

    def nota_envio(self) -> str | None:
        """Aviso para el usuario cuando la tienda no deja cotizar el envío. Por defecto, ninguno."""
        return None
