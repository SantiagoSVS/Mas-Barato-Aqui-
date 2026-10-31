"""Pruebas del cliente HTTP respetuoso: robots.txt (RFC 9309), límite de frecuencia e
identificación del agente."""

import pytest
import requests

from app.extraccion.cliente_http import AccesoNoPermitido, ClienteHttp
from app.extraccion.conector import ErrorConector
from pruebas.falsos import RespuestaFalsa, SesionHttpFalsa

AGENTE = "MasBaratoAquiBot/0.1 (prueba)"
ROBOTS = "https://tienda.example/robots.txt"


class Reloj:
    """Reloj controlado: dormir() avanza el tiempo en lugar de esperar de verdad."""

    def __init__(self) -> None:
        self.ahora = 0.0
        self.esperas: list[float] = []

    def __call__(self) -> float:
        return self.ahora

    def dormir(self, segundos: float) -> None:
        self.esperas.append(segundos)
        self.ahora += segundos


def crear_cliente(respuestas: dict, reloj: Reloj | None = None) -> tuple[ClienteHttp, SesionHttpFalsa]:
    sesion = SesionHttpFalsa(respuestas)
    reloj = reloj or Reloj()
    cliente = ClienteHttp(AGENTE, intervalo_minimo_s=5, timeout_s=20, sesion=sesion, reloj=reloj, dormir=reloj.dormir)
    return cliente, sesion


def test_respeta_las_rutas_prohibidas_en_robots() -> None:
    robots = "User-agent: *\nDisallow: /privado/\n"
    cliente, _ = crear_cliente(
        {ROBOTS: RespuestaFalsa(200, robots), "https://tienda.example/buscar": RespuestaFalsa(200, "ok")}
    )

    assert cliente.get("https://tienda.example/buscar").text == "ok"
    with pytest.raises(AccesoNoPermitido):
        cliente.get("https://tienda.example/privado/cuenta")


def test_respeta_reglas_especificas_para_nuestro_agente() -> None:
    robots = "User-agent: MasBaratoAquiBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    cliente, _ = crear_cliente({ROBOTS: RespuestaFalsa(200, robots)})

    with pytest.raises(AccesoNoPermitido):
        cliente.get("https://tienda.example/buscar")


def test_sin_robots_txt_todo_esta_permitido() -> None:
    cliente, _ = crear_cliente({"https://tienda.example/buscar": RespuestaFalsa(200, "ok")})  # robots → 404

    assert cliente.get("https://tienda.example/buscar").text == "ok"


@pytest.mark.parametrize("falla", [RespuestaFalsa(503), requests.ConnectionError("sin red")])
def test_si_robots_no_se_puede_leer_todo_esta_prohibido(falla) -> None:
    cliente, _ = crear_cliente({ROBOTS: falla, "https://tienda.example/buscar": RespuestaFalsa(200, "ok")})

    with pytest.raises(AccesoNoPermitido):
        cliente.get("https://tienda.example/buscar")


def test_api_oficial_no_consulta_robots() -> None:
    cliente, sesion = crear_cliente({"https://api.example/items": RespuestaFalsa(200, "{}")})

    cliente.get("https://api.example/items", es_api_oficial=True)

    assert [p["url"] for p in sesion.peticiones] == ["https://api.example/items"]


def test_se_identifica_con_su_user_agent_y_usa_timeout() -> None:
    cliente, sesion = crear_cliente({"https://api.example/items": RespuestaFalsa(200)})

    cliente.get("https://api.example/items", encabezados={"Accept": "application/json"}, es_api_oficial=True)

    assert sesion.peticiones[0]["headers"] == {"Accept": "application/json", "User-Agent": AGENTE}
    assert sesion.peticiones[0]["timeout"] == 20


def test_espera_entre_peticiones_al_mismo_dominio() -> None:
    reloj = Reloj()
    cliente, _ = crear_cliente(
        {"https://api.example/a": RespuestaFalsa(200), "https://otra.example/a": RespuestaFalsa(200)}, reloj
    )

    cliente.get("https://api.example/a", es_api_oficial=True)
    reloj.ahora += 2
    cliente.get("https://api.example/a", es_api_oficial=True)  # mismo dominio: espera 3 s más
    cliente.get("https://otra.example/a", es_api_oficial=True)  # otro dominio: no espera

    assert reloj.esperas == [3]


def test_respuesta_de_error_se_convierte_en_error_de_conector() -> None:
    cliente, _ = crear_cliente({"https://api.example/a": RespuestaFalsa(500)})

    with pytest.raises(ErrorConector):
        cliente.get("https://api.example/a", es_api_oficial=True)
