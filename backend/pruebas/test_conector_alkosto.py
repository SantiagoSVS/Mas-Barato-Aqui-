"""Pruebas del conector de Alkosto con una página real guardada (27 de noviembre de 2026,
recortada a los datos del producto)."""

from decimal import Decimal
from pathlib import Path

import pytest

from app.extraccion.cliente_http import AccesoNoPermitido, ClienteHttp
from app.extraccion.conector import ErrorConector
from app.extraccion.conectores.alkosto import URL_BASE, ConectorAlkosto, url_producto
from pruebas.falsos import RespuestaFalsa, SesionHttpFalsa, producto

PAGINA = (Path(__file__).parent / "respuestas" / "alkosto" / "producto_711719574293.html").read_text(encoding="utf-8")
CONTROL = producto("Control Sony DualSense PS5", alkosto=["711719574293"])
# Extracto de las reglas reales: permite productos y prohíbe búsqueda, carrito y checkout
ROBOTS = RespuestaFalsa(200, "User-agent: *\nAllow: /\nDisallow: *?q=\nDisallow: /checkout\nDisallow: /search/\n")


def crear(paginas: dict[str, RespuestaFalsa]) -> tuple[ConectorAlkosto, SesionHttpFalsa]:
    sesion = SesionHttpFalsa({f"{URL_BASE}/robots.txt": ROBOTS, **paginas})
    cliente = ClienteHttp("prueba", intervalo_minimo_s=0, timeout_s=5, sesion=sesion)
    return ConectorAlkosto(cliente), sesion


def leer(pagina: str):
    conector, _ = crear({url_producto("711719574293"): RespuestaFalsa(200, pagina)})
    return conector.buscar(CONTROL)


def test_lee_nombre_precio_vendedor_disponibilidad_y_envio() -> None:
    [oferta] = leer(PAGINA)

    assert oferta.titulo == "Control PLAYSTATION PS5 DualSense Blanco"
    assert oferta.precio == Decimal("249900")
    assert oferta.moneda == "COP"
    assert oferta.vendedor == "Alkosto"
    assert oferta.disponible is True
    assert str(oferta.url) == "https://www.alkosto.com/p/711719574293"


def test_toma_el_envio_a_domicilio_y_suma_alistamiento_y_transito() -> None:
    # La página publica envío gratis con 0 días de alistamiento y 1 de tránsito
    [oferta] = leer(PAGINA)

    assert oferta.envio == Decimal("0")
    assert oferta.dias_entrega == 1


def test_un_envio_con_costo_se_lee_tal_cual() -> None:
    pagina = PAGINA.replace('<meta itemprop="value" content="0.0">', '<meta itemprop="value" content="12900.0">', 1)

    assert leer(pagina)[0].envio == Decimal("12900")


def test_recoger_en_tienda_no_cuenta_como_envio() -> None:
    # Sin la opción de envío a domicilio, el envío queda desconocido aunque se pueda recoger gratis
    inicio = PAGINA.index('itemprop="shippingDetails"')
    segundo = PAGINA.index('itemprop="shippingDetails"', inicio + 1)
    pagina = PAGINA[:inicio] + PAGINA[segundo:]

    [oferta] = leer(pagina)

    assert oferta.envio is None and oferta.dias_entrega is None


def test_producto_agotado_queda_no_disponible() -> None:
    pagina = PAGINA.replace("https://schema.org/InStock", "https://schema.org/OutOfStock")

    assert leer(pagina)[0].disponible is False


def test_si_la_pagina_es_de_otro_producto_no_se_mezcla() -> None:
    pagina = PAGINA.replace(">711719574293</span>", ">711719574309</span>")

    with pytest.raises(ErrorConector, match="otro producto"):
        leer(pagina)


def test_si_la_pagina_cambia_avisa_en_lugar_de_inventar() -> None:
    with pytest.raises(ErrorConector, match="cambió"):
        leer("<html><body>Página nueva</body></html>")


def test_un_producto_retirado_no_devuelve_oferta() -> None:
    conector, _ = crear({url_producto("711719574293"): RespuestaFalsa(404, "")})

    assert conector.buscar(CONTROL) == []


def test_sin_identificador_de_alkosto_no_hace_peticiones() -> None:
    conector, sesion = crear({})

    assert conector.buscar(producto("Otro producto", falabella=["1"])) == []
    assert sesion.peticiones == []


def test_respeta_robots_txt() -> None:
    sesion = SesionHttpFalsa({f"{URL_BASE}/robots.txt": RespuestaFalsa(200, "User-agent: *\nDisallow: /p/\n")})
    conector = ConectorAlkosto(ClienteHttp("prueba", intervalo_minimo_s=0, timeout_s=5, sesion=sesion))

    with pytest.raises(AccesoNoPermitido):
        conector.buscar(CONTROL)


def test_actualizar_lee_el_codigo_de_la_direccion() -> None:
    conector, _ = crear({url_producto("711719574293"): RespuestaFalsa(200, PAGINA)})

    oferta = conector.actualizar("https://www.alkosto.com/control-playstation-ps5-dualsense-blanco/p/711719574293")

    assert oferta is not None and oferta.precio == Decimal("249900")
