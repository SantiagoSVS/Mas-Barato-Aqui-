"""Pruebas del conector de Falabella con una página real guardada (1 de noviembre de 2026,
recortada a los datos que usa el conector)."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.extraccion.cliente_http import AccesoNoPermitido, ClienteHttp
from app.extraccion.conector import ErrorConector
from app.extraccion.conectores.falabella import URL_BASE, ConectorFalabella, url_producto
from pruebas.falsos import RespuestaFalsa, SesionHttpFalsa, producto

PAGINA = (Path(__file__).parent / "respuestas" / "falabella" / "producto_73336565.html").read_text(encoding="utf-8")
FREIDORA = producto("Freidora Holstein 9 L", categoria="hogar", falabella=["73336565"])
ROBOTS = RespuestaFalsa(200, "User-agent: *\nDisallow: /falabella-co/checkout*\n")


def pagina_con(cambiar) -> str:
    """Copia de la página guardada con una modificación en su __NEXT_DATA__."""
    inicio = PAGINA.index(">", PAGINA.index('id="__NEXT_DATA__"')) + 1
    fin = PAGINA.index("</script>", inicio)
    datos = json.loads(PAGINA[inicio:fin])
    cambiar(datos["props"]["pageProps"]["productData"])
    return PAGINA[:inicio] + json.dumps(datos, ensure_ascii=False) + PAGINA[fin:]


def crear(paginas: dict[str, RespuestaFalsa]) -> tuple[ConectorFalabella, SesionHttpFalsa]:
    sesion = SesionHttpFalsa({f"{URL_BASE}/robots.txt": ROBOTS, **paginas})
    cliente = ClienteHttp("prueba", intervalo_minimo_s=0, timeout_s=5, sesion=sesion)
    return ConectorFalabella(cliente), sesion


def test_lee_nombre_precio_vendedor_y_disponibilidad() -> None:
    conector, _ = crear({url_producto("73336565"): RespuestaFalsa(200, PAGINA)})

    [oferta] = conector.buscar(FREIDORA)

    assert oferta.titulo == "Freidora de Aire Holstein 9 Litros Doble Canasta"
    assert oferta.precio == Decimal("299900")  # precio internet; el tachado de $599.900 no cuenta
    assert oferta.moneda == "COP"
    assert oferta.vendedor == "FALABELLA"
    assert oferta.disponible is True
    assert str(oferta.url) == "https://www.falabella.com.co/falabella-co/product/73336565"


def test_envio_y_dias_quedan_desconocidos() -> None:
    conector, _ = crear({url_producto("73336565"): RespuestaFalsa(200, PAGINA)})

    [oferta] = conector.buscar(FREIDORA)

    assert oferta.envio is None
    assert oferta.dias_entrega is None


def test_publica_el_aviso_de_envio_gratis_de_la_pagina() -> None:
    conector, _ = crear({url_producto("73336565"): RespuestaFalsa(200, PAGINA)})
    assert conector.nota_envio() is None  # aún no ha leído ninguna página

    conector.buscar(FREIDORA)

    assert "envío gratis desde $149.000" in conector.nota_envio()
    assert "no aplica a todos los productos" in conector.nota_envio()


def test_ignora_el_precio_con_tarjeta_cmr() -> None:
    def agregar_precio_cmr(datos: dict) -> None:
        datos["variants"][0]["prices"].append({"type": "cmrPrice", "crossed": False, "price": ["279.900"]})

    conector, _ = crear({url_producto("73336565"): RespuestaFalsa(200, pagina_con(agregar_precio_cmr))})

    [oferta] = conector.buscar(FREIDORA)

    assert oferta.precio == Decimal("299900")


def test_toma_el_menor_precio_vigente() -> None:
    def agregar_precio_evento(datos: dict) -> None:
        datos["variants"][0]["prices"].append({"type": "eventPrice", "crossed": False, "price": ["289.900"]})

    conector, _ = crear({url_producto("73336565"): RespuestaFalsa(200, pagina_con(agregar_precio_evento))})

    assert conector.buscar(FREIDORA)[0].precio == Decimal("289900")


def test_producto_agotado_queda_no_disponible() -> None:
    def agotar(datos: dict) -> None:
        datos["isOutOfStock"] = True

    conector, _ = crear({url_producto("73336565"): RespuestaFalsa(200, pagina_con(agotar))})

    assert conector.buscar(FREIDORA)[0].disponible is False


def test_producto_que_ya_no_existe_se_omite() -> None:
    conector, _ = crear({})  # la página responde 404

    assert conector.buscar(FREIDORA) == []


def test_producto_sin_identificador_de_falabella_no_consulta_la_tienda() -> None:
    conector, sesion = crear({})

    assert conector.buscar(producto("Solo en Mercado Libre", mercadolibre=["MCO1"])) == []
    assert sesion.peticiones == []


def test_si_la_pagina_cambia_de_estructura_lanza_error_de_conector() -> None:
    conector, _ = crear({url_producto("73336565"): RespuestaFalsa(200, "<html>sin datos</html>")})

    with pytest.raises(ErrorConector, match="__NEXT_DATA__"):
        conector.buscar(FREIDORA)


def test_respeta_robots_txt() -> None:
    sesion = SesionHttpFalsa(
        {f"{URL_BASE}/robots.txt": RespuestaFalsa(200, "User-agent: *\nDisallow: /\n"),
         url_producto("73336565"): RespuestaFalsa(200, PAGINA)}
    )
    conector = ConectorFalabella(ClienteHttp("prueba", intervalo_minimo_s=0, timeout_s=5, sesion=sesion))

    with pytest.raises(AccesoNoPermitido):
        conector.buscar(FREIDORA)


def test_actualizar_lee_el_producto_desde_su_url() -> None:
    conector, _ = crear({url_producto("73336565"): RespuestaFalsa(200, PAGINA)})

    oferta = conector.actualizar("https://www.falabella.com.co/falabella-co/product/73336565/Freidora-de-Aire")

    assert oferta.precio == Decimal("299900")
