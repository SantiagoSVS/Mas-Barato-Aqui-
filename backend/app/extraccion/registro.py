"""Registro de conectores disponibles, por nombre de plataforma.

Para integrar una tienda se escribe su conector (una clase que hereda de Conector) y se
agrega aquí su fábrica. Nada más del sistema cambia (RNF-06).

Cada fábrica devuelve None si a la tienda le falta configuración (por ejemplo, credenciales);
en ese caso el worker la omite y lo deja en el log.
"""

from collections.abc import Callable

from app.config import Configuracion
from app.extraccion.cliente_http import ClienteHttp
from app.extraccion.conector import Conector
from app.extraccion.conectores.falabella import ConectorFalabella
from app.extraccion.conectores.mercadolibre import ConectorMercadoLibre

FabricaConector = Callable[[ClienteHttp, Configuracion], Conector | None]


def _mercadolibre(cliente: ClienteHttp, configuracion: Configuracion) -> Conector | None:
    if not (configuracion.mercadolibre_client_id and configuracion.mercadolibre_client_secret):
        return None
    return ConectorMercadoLibre(
        cliente,
        client_id=configuracion.mercadolibre_client_id,
        client_secret=configuracion.mercadolibre_client_secret,
        ciudad_destino=configuracion.mercadolibre_ciudad_destino,
        ofertas_por_producto=configuracion.mercadolibre_ofertas_por_producto,
    )


def _falabella(cliente: ClienteHttp, configuracion: Configuracion) -> Conector | None:
    return ConectorFalabella(cliente)  # no necesita credenciales


# Amazon no se integra mientras el proyecto sea de grado (decisión del 1 de noviembre de 2026):
# su acceso es complejo. Sigue en los documentos, y la conversión USD→COP (TRM) queda lista.
CONECTORES: dict[str, FabricaConector] = {
    ConectorMercadoLibre.nombre_plataforma: _mercadolibre,
    ConectorFalabella.nombre_plataforma: _falabella,
}


def crear_conectores(cliente: ClienteHttp, configuracion: Configuracion) -> dict[str, Conector]:
    conectores = {}
    for nombre, fabrica in CONECTORES.items():
        conector = fabrica(cliente, configuracion)
        if conector is not None:
            conectores[nombre] = conector
    return conectores
