"""Formato común en que todos los conectores entregan las ofertas."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

MONEDAS_SOPORTADAS = ("COP", "USD")


class OfertaCapturada(BaseModel):
    """Oferta tal como la ve la tienda, antes de normalizar.

    precio y envio van en la moneda de la tienda. envio y dias_entrega quedan en None
    cuando la tienda no los muestra: nunca se suponen.
    """

    titulo: str = Field(min_length=1)
    url: HttpUrl
    vendedor: str | None = None
    precio: Decimal = Field(ge=0)
    moneda: Literal["COP", "USD"]
    envio: Decimal | None = Field(default=None, ge=0)
    dias_entrega: int | None = Field(default=None, ge=0)
    disponible: bool = True


class OfertaNormalizada(BaseModel):
    """Oferta lista para guardar: valores en pesos colombianos enteros.

    Para ofertas en otra moneda conserva el precio original y la tasa usada (trazabilidad).
    """

    titulo: str
    url: str
    vendedor: str | None
    precio_cop: int
    envio_cop: int | None
    dias_entrega: int | None
    disponible: bool
    precio_original: Decimal | None = None
    moneda_original: str | None = None
    tasa_cambio: Decimal | None = None
