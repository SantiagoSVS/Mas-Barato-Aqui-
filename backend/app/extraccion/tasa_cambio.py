"""Tasa de cambio para convertir a pesos las ofertas en dólares (Amazon, RF-04).

Se usa la TRM (Tasa Representativa del Mercado) que certifica la Superintendencia
Financiera, publicada como datos abiertos en datos.gov.co. Es la fuente oficial en Colombia.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from app.extraccion.cliente_http import ClienteHttp
from app.extraccion.conector import ErrorConector

URL_TRM = "https://www.datos.gov.co/resource/32sa-8pi3.json"


@dataclass(frozen=True)
class TasaCambio:
    moneda: str  # moneda de origen; la de destino siempre es COP
    valor: Decimal  # pesos por una unidad de la moneda de origen
    fecha: date
    fuente: str


class ErrorTasaCambio(ErrorConector):
    """No se pudo obtener la tasa de cambio del día."""


class ProveedorTasaCambio(ABC):
    @abstractmethod
    def obtener(self, moneda: str, fecha: date) -> TasaCambio:
        """Tasa vigente en esa fecha. Lanza ErrorTasaCambio si no la encuentra."""


class ProveedorTRM(ProveedorTasaCambio):
    """TRM oficial (dólar a peso colombiano) desde datos.gov.co."""

    def __init__(self, cliente: ClienteHttp) -> None:
        self._cliente = cliente
        self._cache: dict[date, TasaCambio] = {}

    def obtener(self, moneda: str, fecha: date) -> TasaCambio:
        if moneda != "USD":
            raise ErrorTasaCambio(f"La TRM solo convierte dólares, no {moneda}")
        if fecha not in self._cache:
            self._cache[fecha] = self._consultar(fecha)
        return self._cache[fecha]

    def _consultar(self, fecha: date) -> TasaCambio:
        # Cada registro tiene un rango de vigencia (los fines de semana comparten la TRM)
        dia = f"{fecha.isoformat()}T00:00:00"
        try:
            respuesta = self._cliente.get(
                URL_TRM,
                params={"$where": f"vigenciadesde <= '{dia}' AND vigenciahasta >= '{dia}'"},
                es_api_oficial=True,
            )
        except ErrorConector as error:
            raise ErrorTasaCambio(f"No se pudo consultar la TRM: {error}") from error
        try:
            registros = respuesta.json()
        except ValueError as error:
            raise ErrorTasaCambio("La respuesta de la TRM no es JSON válido") from error

        if len(registros) != 1:
            raise ErrorTasaCambio(f"Se esperaba una TRM para {fecha}, llegaron {len(registros)}")
        registro = registros[0]
        if registro.get("unidad") != "COP":
            raise ErrorTasaCambio(f"Unidad de TRM inesperada: {registro.get('unidad')!r}")
        try:
            valor = Decimal(registro["valor"])
        except (KeyError, InvalidOperation) as error:
            raise ErrorTasaCambio(f"Valor de TRM no válido: {registro!r}") from error
        if valor <= 0:
            raise ErrorTasaCambio(f"Valor de TRM no válido: {valor}")

        return TasaCambio(moneda="USD", valor=valor, fecha=fecha, fuente="TRM datos.gov.co")
