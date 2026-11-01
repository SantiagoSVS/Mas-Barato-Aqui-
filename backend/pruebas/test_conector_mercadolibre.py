"""Pruebas del conector de Mercado Libre con respuestas reales guardadas de su API
(capturadas el 1 de noviembre de 2026, recortadas y sin datos de la cuenta)."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.extraccion.cliente_http import ClienteHttp
from app.extraccion.conector import ErrorConector
from app.extraccion.conectores.mercadolibre import URL_API, ConectorMercadoLibre, url_publicacion
from pruebas.falsos import RespuestaFalsa, SesionHttpFalsa

RESPUESTAS = Path(__file__).parent / "respuestas" / "mercadolibre"
PRODUCTO_SIN_PUBLICACIONES = "MCO63264851"
PRODUCTO = "MCO56570140"
ITEM_1, ITEM_2 = "MCO4113792896", "MCO3540893672"
TOKEN = RespuestaFalsa(200, datos={"access_token": "token-de-prueba", "expires_in": 21600})


def guardada(nombre: str) -> RespuestaFalsa:
    return RespuestaFalsa(200, datos=json.loads((RESPUESTAS / nombre).read_text(encoding="utf-8")))


def respuestas_completas() -> dict:
    return {
        f"{URL_API}/oauth/token": TOKEN,
        f"{URL_API}/products/search": guardada("products_search.json"),
        f"{URL_API}/products/{PRODUCTO_SIN_PUBLICACIONES}/items": RespuestaFalsa(404),
        f"{URL_API}/products/{PRODUCTO}/items": guardada("product_items.json"),
        f"{URL_API}/items/{ITEM_1}/shipping_options": guardada("shipping_options.json"),
        # ITEM_2 sin opciones de envío disponibles (404)
    }


class Reloj:
    def __init__(self) -> None:
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


def crear(respuestas: dict, reloj: Reloj | None = None) -> tuple[ConectorMercadoLibre, SesionHttpFalsa]:
    sesion = SesionHttpFalsa(respuestas)
    cliente = ClienteHttp("prueba", intervalo_minimo_s=0, timeout_s=5, sesion=sesion)
    conector = ConectorMercadoLibre(
        cliente,
        client_id="id",
        client_secret="secreto",
        ciudad_destino="TUNPQ01FRGRjNjc4",
        productos_por_termino=5,
        ofertas_por_producto=5,
        hoy=lambda: date(2026, 11, 1),
        reloj=reloj or Reloj(),
    )
    return conector, sesion


def test_url_publicacion() -> None:
    assert url_publicacion("MCO4113792896") == "https://articulo.mercadolibre.com.co/MCO-4113792896"


def test_buscar_devuelve_las_publicaciones_con_precio_envio_y_dias() -> None:
    conector, _ = crear(respuestas_completas())

    ofertas = conector.buscar("Samsung Galaxy A55 128GB")

    assert [str(o.url) for o in ofertas] == [url_publicacion(ITEM_1), url_publicacion(ITEM_2)]
    primera = ofertas[0]
    assert primera.precio == Decimal("524900")
    assert primera.moneda == "COP"
    assert primera.envio == Decimal("0")
    assert primera.dias_entrega == 2  # entrega estimada el 3 de noviembre
    assert primera.vendedor == "162681369"
    assert "Samsung" in primera.titulo


def test_sin_opciones_de_envio_el_envio_y_los_dias_quedan_desconocidos() -> None:
    conector, _ = crear(respuestas_completas())

    segunda = conector.buscar("Samsung Galaxy A55 128GB")[1]

    assert segunda.envio is None
    assert segunda.dias_entrega is None


def test_usa_el_token_y_la_ciudad_de_destino_sin_consultar_robots() -> None:
    conector, sesion = crear(respuestas_completas())

    conector.buscar("Samsung Galaxy A55 128GB")

    urls = [p["url"] for p in sesion.peticiones]
    assert not any(u.endswith("robots.txt") for u in urls)
    busqueda = next(p for p in sesion.peticiones if p["url"].endswith("/products/search"))
    assert busqueda["headers"]["Authorization"] == "Bearer token-de-prueba"
    assert busqueda["params"]["site_id"] == "MCO"
    envio = next(p for p in sesion.peticiones if "shipping_options" in p["url"])
    assert envio["params"] == {"city_to": "TUNPQ01FRGRjNjc4"}


def test_el_token_se_reutiliza_hasta_que_vence() -> None:
    reloj = Reloj()
    conector, sesion = crear(respuestas_completas(), reloj)

    conector.buscar("a")
    conector.buscar("b")
    reloj.ahora += 21600  # 6 horas después
    conector.buscar("c")

    pedidos_token = [p for p in sesion.peticiones if p["url"].endswith("/oauth/token")]
    assert len(pedidos_token) == 2
    assert pedidos_token[0]["data"]["grant_type"] == "client_credentials"


def test_omite_publicaciones_usadas() -> None:
    respuestas = respuestas_completas()
    items = json.loads((RESPUESTAS / "product_items.json").read_text(encoding="utf-8"))
    items["results"][0]["condition"] = "used"
    respuestas[f"{URL_API}/products/{PRODUCTO}/items"] = RespuestaFalsa(200, datos=items)
    conector, _ = crear(respuestas)

    ofertas = conector.buscar("Samsung Galaxy A55 128GB")

    assert [str(o.url) for o in ofertas] == [url_publicacion(ITEM_2)]


def test_si_la_busqueda_falla_lanza_error_de_conector() -> None:
    respuestas = respuestas_completas()
    respuestas[f"{URL_API}/products/search"] = RespuestaFalsa(500)
    conector, _ = crear(respuestas)

    with pytest.raises(ErrorConector):
        conector.buscar("celular")


def test_credenciales_invalidas_lanzan_error_de_conector() -> None:
    respuestas = respuestas_completas()
    respuestas[f"{URL_API}/oauth/token"] = RespuestaFalsa(400)
    conector, _ = crear(respuestas)

    with pytest.raises(ErrorConector):
        conector.buscar("celular")
