"""Normalización de los datos capturados (RF-04, sección 5.2).

Convierte precios a pesos colombianos enteros, aplica la tasa de cambio a las ofertas en
dólares y unifica cómo se escriben las unidades en los títulos.
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.extraccion.tasa_cambio import TasaCambio
from app.extraccion.tipos import OfertaCapturada, OfertaNormalizada


class ErrorNormalizacion(ValueError):
    """El dato no se puede normalizar sin suponer algo; la oferta se omite."""


def parsear_precio_cop(texto: str) -> int:
    """Lee un precio escrito al estilo colombiano: "$ 789.900", "789.900", "$1.299.900,00".

    El punto separa miles y la coma separa decimales. Los centavos se redondean.
    """
    limpio = re.sub(r"[^\d.,]", "", texto)
    if not re.fullmatch(r"\d{1,3}(\.\d{3})*(,\d+)?|\d+(,\d+)?", limpio):
        raise ErrorNormalizacion(f"Precio en pesos no reconocido: {texto!r}")
    return redondear_a_peso(Decimal(limpio.replace(".", "").replace(",", ".")))


def parsear_precio_usd(texto: str) -> Decimal:
    """Lee un precio en dólares: "US$ 1,234.56", "$735.00", "735".

    La coma separa miles y el punto separa decimales.
    """
    limpio = re.sub(r"[^\d.,]", "", texto)
    if not re.fullmatch(r"\d{1,3}(,\d{3})*(\.\d{1,2})?|\d+(\.\d{1,2})?", limpio):
        raise ErrorNormalizacion(f"Precio en dólares no reconocido: {texto!r}")
    return Decimal(limpio.replace(",", ""))


def redondear_a_peso(valor: Decimal) -> int:
    """Redondea al peso más cercano (0,5 hacia arriba)."""
    try:
        return int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except InvalidOperation as error:
        raise ErrorNormalizacion(f"Valor no numérico: {valor!r}") from error


# "128gb", "128 Gb", "1tb" -> "128 GB", "1 TB"
_UNIDADES = re.compile(r"(\d+(?:[.,]\d+)?)\s*(gb|tb|mb|mah|w|hz|ghz|mp)\b", re.IGNORECASE)
_ESCRITURA_UNIDAD = {"gb": "GB", "tb": "TB", "mb": "MB", "mah": "mAh", "w": "W", "hz": "Hz", "ghz": "GHz", "mp": "MP"}


def normalizar_titulo(titulo: str) -> str:
    """Unifica espacios y la escritura de las unidades, sin cambiar el resto del texto."""
    titulo = " ".join(titulo.split())
    return _UNIDADES.sub(lambda m: f"{m.group(1)} {_ESCRITURA_UNIDAD[m.group(2).lower()]}", titulo)


def normalizar_oferta(oferta: OfertaCapturada, tasa: TasaCambio | None) -> OfertaNormalizada:
    """Convierte una oferta al formato que se guarda en la base de datos.

    Las ofertas en dólares necesitan la tasa del día de la captura. Si no hay tasa, la oferta
    no se puede convertir y se rechaza: nunca se usa una tasa supuesta.
    """
    comunes = {
        "titulo": normalizar_titulo(oferta.titulo),
        "url": str(oferta.url),
        "vendedor": oferta.vendedor,
        "dias_entrega": oferta.dias_entrega,
        "disponible": oferta.disponible,
    }

    if oferta.moneda == "COP":
        return OfertaNormalizada(
            **comunes,
            precio_cop=redondear_a_peso(oferta.precio),
            envio_cop=None if oferta.envio is None else redondear_a_peso(oferta.envio),
        )

    if tasa is None or tasa.moneda != oferta.moneda:
        raise ErrorNormalizacion(f"No hay tasa de cambio {oferta.moneda}→COP para convertir la oferta")

    return OfertaNormalizada(
        **comunes,
        precio_cop=redondear_a_peso(oferta.precio * tasa.valor),
        envio_cop=None if oferta.envio is None else redondear_a_peso(oferta.envio * tasa.valor),
        precio_original=oferta.precio,
        moneda_original=oferta.moneda,
        tasa_cambio=tasa.valor,
    )
