"""Pruebas del conector de Homecenter con una página real guardada (1 de noviembre de 2026,
recortada a los datos que usa el conector)."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.extraccion.cliente_http import AccesoNoPermitido, ClienteHttp
from app.extraccion.conector import ErrorConector
from app.extraccion.conectores.homecenter import NOTA_ENVIO, URL_BASE, ConectorHomecenter, url_producto
from pruebas.falsos import RespuestaFalsa, SesionHttpFalsa, producto

PAGINA = (Path(__file__).parent / "respuestas" / "homecenter" / "producto_3111000.html").read_text(encoding="utf-8")
FREIDORA = producto("Freidora Ninja 5,7 L", categoria="hogar", homecenter=["3111000"])
# Extracto de las reglas reales: permite productos y prohíbe la búsqueda
ROBOTS = RespuestaFalsa(200, "User-agent: *\nDisallow: /homecenter-co/search/\nDisallow: */search?\n")


def pagina_con(cambiar) -> str:
    """Copia de la página guardada con una modificación en la variante principal."""
    inicio = PAGINA.index(">", PAGINA.index('id="__NEXT_DATA__"')) + 1
    fin = PAGINA.index("</script>", inicio)
    datos = json.loads(PAGINA[inicio:fin])
    cambiar(datos["props"]["pageProps"]["productProps"]["result"]["variants"][0])
    return PAGINA[:inicio] + json.dumps(datos, ensure_ascii=False) + PAGINA[fin:]


def crear(paginas: dict[str, RespuestaFalsa]) -> tuple[ConectorHomecenter, SesionHttpFalsa]:
    sesion = SesionHttpFalsa({f"{URL_BASE}/robots.txt": ROBOTS, **paginas})
    cliente = ClienteHttp("prueba", intervalo_minimo_s=0, timeout_s=5, sesion=sesion)
    return ConectorHomecenter(cliente), sesion


def test_lee_nombre_precio_vendedor_y_disponibilidad() -> None:
    conector, _ = crear({url_producto("3111000"): RespuestaFalsa(200, PAGINA)})

    [oferta] = conector.buscar(FREIDORA)

    assert oferta.titulo.startswith("Freidora de Aire En Vidrio Crispi Ninja")
    assert oferta.precio == Decimal("1299900")
    assert oferta.vendedor == "Homecenter"
    assert oferta.disponible is True
    assert oferta.envio is None and oferta.dias_entrega is None
    assert str(oferta.url) == "https://www.homecenter.com.co/homecenter-co/product/3111000"


def test_toma_el_precio_internet_si_es_menor_que_el_normal() -> None:
    def agregar_internet(variante: dict) -> None:
        variante["price"].append({"type": "INTERNET", "price": "1.099.900"})

    conector, _ = crear({url_producto("3111000"): RespuestaFalsa(200, pagina_con(agregar_internet))})

    assert conector.buscar(FREIDORA)[0].precio == Decimal("1099900")


def test_ignora_el_precio_con_tarjeta_cmr() -> None:
    def agregar_cmr(variante: dict) -> None:
        variante["price"].append({"type": "CMR", "price": "999.900"})

    conector, _ = crear({url_producto("3111000"): RespuestaFalsa(200, pagina_con(agregar_cmr))})

    assert conector.buscar(FREIDORA)[0].precio == Decimal("1299900")


def test_sin_stock_para_envio_queda_no_disponible() -> None:
    def sin_stock(variante: dict) -> None:
        variante["availability"] = [{"hasStock": False, "shippingType": "homeDelivery"}]

    conector, _ = crear({url_producto("3111000"): RespuestaFalsa(200, pagina_con(sin_stock))})

    assert conector.buscar(FREIDORA)[0].disponible is False


def test_siempre_publica_el_aviso_de_envio() -> None:
    conector, _ = crear({})

    assert conector.nota_envio() == NOTA_ENVIO


def test_producto_que_ya_no_existe_se_omite() -> None:
    conector, _ = crear({})  # la página responde 404

    assert conector.buscar(FREIDORA) == []


def test_si_la_pagina_cambia_de_estructura_lanza_error_de_conector() -> None:
    conector, _ = crear({url_producto("3111000"): RespuestaFalsa(200, "<html>sin datos</html>")})

    with pytest.raises(ErrorConector, match="__NEXT_DATA__"):
        conector.buscar(FREIDORA)


def test_robots_prohibe_la_busqueda_de_homecenter() -> None:
    conector, _ = crear({})

    with pytest.raises(AccesoNoPermitido):
        conector._cliente.get(f"{URL_BASE}/homecenter-co/search?Ntt=freidora")


def test_producto_sin_identificador_de_homecenter_no_consulta_la_tienda() -> None:
    conector, sesion = crear({})

    assert conector.buscar(producto("Solo en Falabella", falabella=["1"])) == []
    assert sesion.peticiones == []
