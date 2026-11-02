"""Interfaz del proveedor del modelo de lenguaje.

El proveedor real aún no se ha elegido (sección 4: "decisión pendiente"). Todo el sistema
habla con esta interfaz, así que el proveedor se cambia por configuración sin tocar el resto.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RespuestaModelo:
    texto: str  # se espera un objeto JSON; el intérprete lo valida
    tokens_entrada: int
    tokens_salida: int


class ErrorProveedor(Exception):
    """El proveedor no respondió (red, cuota, clave inválida)."""


class ProveedorModelo(ABC):
    nombre: str

    @abstractmethod
    def completar(self, instrucciones: str, consulta: str) -> RespuestaModelo:
        """Envía las instrucciones y la consulta del usuario; devuelve el texto de respuesta."""
