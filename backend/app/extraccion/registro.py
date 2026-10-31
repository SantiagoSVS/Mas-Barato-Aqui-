"""Registro de conectores disponibles, por nombre de plataforma.

Para integrar una tienda se escribe su conector (una clase que hereda de Conector) y se
agrega aquí una línea. Nada más del sistema cambia (RNF-06).
"""

from collections.abc import Callable

from app.extraccion.cliente_http import ClienteHttp
from app.extraccion.conector import Conector

FabricaConector = Callable[[ClienteHttp], Conector]

# PENDIENTE: Mercado Libre, Falabella y Amazon, cuando estén definidos sus accesos.
CONECTORES: dict[str, FabricaConector] = {}
