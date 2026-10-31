"""Interfaz común de los conectores (RNF-06: agregar una tienda = escribir un conector).

Cada tienda tiene una clase que hereda de Conector e implementa buscar() y actualizar().
El resto del sistema (worker, normalización, base de datos) solo conoce esta interfaz.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from app.extraccion.tipos import OfertaCapturada


class ErrorConector(Exception):
    """Falla al consultar una tienda: sitio caído, respuesta inesperada, acceso no permitido."""


class Conector(ABC):
    # Debe coincidir con plataforma.nombre en la base de datos
    nombre_plataforma: ClassVar[str]

    @abstractmethod
    def buscar(self, termino: str) -> list[OfertaCapturada]:
        """Busca un término del catálogo y devuelve las ofertas encontradas."""

    @abstractmethod
    def actualizar(self, url: str) -> OfertaCapturada | None:
        """Vuelve a consultar una oferta ya conocida. None si ya no existe."""
