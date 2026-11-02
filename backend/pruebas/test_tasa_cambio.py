"""Pruebas del proveedor de TRM con respuestas reales guardadas de datos.gov.co."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.extraccion.cliente_http import ClienteHttp
from app.extraccion.tasa_cambio import URL_TRM, ErrorTasaCambio, ProveedorTRM
from pruebas.falsos import RespuestaFalsa, SesionHttpFalsa

RESPUESTAS = Path(__file__).parent / "respuestas"


def proveedor_con(respuesta: RespuestaFalsa) -> tuple[ProveedorTRM, SesionHttpFalsa]:
    sesion = SesionHttpFalsa({URL_TRM: respuesta})
    cliente = ClienteHttp("prueba", intervalo_minimo_s=0, timeout_s=5, sesion=sesion)
    return ProveedorTRM(cliente), sesion


def respuesta_guardada(nombre: str) -> RespuestaFalsa:
    return RespuestaFalsa(200, datos=json.loads((RESPUESTAS / nombre).read_text(encoding="utf-8")))


def test_lee_la_trm_del_dia() -> None:
    proveedor, sesion = proveedor_con(respuesta_guardada("trm_2026-10-30.json"))

    tasa = proveedor.obtener("USD", date(2026, 10, 30))

    assert tasa.valor == Decimal("3166.91")
    assert tasa.fecha == date(2026, 10, 30)
    assert "2026-10-30T00:00:00" in sesion.peticiones[0]["params"]["$where"]


def test_fin_de_semana_usa_la_trm_vigente() -> None:
    # La TRM publicada el 31 de octubre rige hasta el 3 de noviembre
    proveedor, _ = proveedor_con(respuesta_guardada("trm_2026-11-01.json"))

    assert proveedor.obtener("USD", date(2026, 11, 1)).valor == Decimal("3182.99")


def test_consulta_una_sola_vez_por_dia() -> None:
    proveedor, sesion = proveedor_con(respuesta_guardada("trm_2026-10-30.json"))

    proveedor.obtener("USD", date(2026, 10, 30))
    proveedor.obtener("USD", date(2026, 10, 30))

    assert len(sesion.peticiones) == 1


@pytest.mark.parametrize(
    "respuesta",
    [
        RespuestaFalsa(200, datos=[]),
        RespuestaFalsa(200, datos=[{"valor": "abc", "unidad": "COP"}]),
        RespuestaFalsa(200, datos=[{"valor": "4000", "unidad": "EUR"}]),
        RespuestaFalsa(200, text="<html>"),
        RespuestaFalsa(500),
    ],
)
def test_respuestas_invalidas_lanzan_error(respuesta: RespuestaFalsa) -> None:
    proveedor, _ = proveedor_con(respuesta)

    with pytest.raises(ErrorTasaCambio):
        proveedor.obtener("USD", date(2026, 10, 30))


def test_solo_convierte_dolares() -> None:
    proveedor, _ = proveedor_con(respuesta_guardada("trm_2026-10-30.json"))

    with pytest.raises(ErrorTasaCambio):
        proveedor.obtener("EUR", date(2026, 10, 30))
