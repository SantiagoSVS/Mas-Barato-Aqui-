"""Pruebas de GET /salud."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import obtener_sesion
from app.main import app
from app.modelos import Captura, EjecucionCaptura, Oferta, Plataforma


def por_nombre(cuerpo: dict) -> dict[str, dict]:
    return {p["nombre"]: p for p in cuerpo["plataformas"]}


def test_responde_ok_con_las_plataformas_registradas(cliente: TestClient) -> None:
    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert (cuerpo["estado"], cuerpo["base_de_datos"]) == ("ok", "ok")
    # Mercado Libre la registra una migración; en la base de pruebas no tiene capturas
    assert por_nombre(cuerpo)["Mercado Libre"] == {
        "nombre": "Mercado Libre",
        "activa": True,
        "ultima_captura": None,
        "ultima_ejecucion": None,
    }


def test_muestra_la_ultima_captura_de_cada_plataforma(
    cliente: TestClient, sesion: Session
) -> None:
    # Datos de prueba, no son precios reales
    con_capturas = Plataforma(
        nombre="Tienda A", tipo_acceso="api", url_base="https://a.example", moneda="COP"
    )
    sin_capturas = Plataforma(
        nombre="Tienda B", tipo_acceso="extraccion", url_base="https://b.example", moneda="COP"
    )
    oferta = Oferta(
        plataforma=con_capturas, titulo_original="Producto X", url_origen="https://a.example/x"
    )
    anterior = datetime(2026, 10, 30, 10, 0, tzinfo=UTC)
    reciente = datetime(2026, 10, 31, 10, 0, tzinfo=UTC)
    for momento in (anterior, reciente):
        sesion.add(Captura(oferta=oferta, capturado_en=momento, precio_cop=100, disponible=True))
    sesion.add_all([con_capturas, sin_capturas])
    sesion.flush()

    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    plataformas = por_nombre(respuesta.json())
    assert datetime.fromisoformat(plataformas["Tienda A"]["ultima_captura"]) == reciente
    assert plataformas["Tienda B"]["ultima_captura"] is None


def test_muestra_el_estado_de_la_ultima_ejecucion(cliente: TestClient, sesion: Session) -> None:
    tienda = Plataforma(nombre="Tienda A", tipo_acceso="api", url_base="https://a.example", moneda="COP")
    for dia, estado, mensaje in ((30, "exitosa", None), (31, "fallida", "la tienda no respondió")):
        momento = datetime(2026, 10, dia, 10, 0, tzinfo=UTC)
        sesion.add(
            EjecucionCaptura(
                plataforma=tienda,
                iniciada_en=momento,
                terminada_en=momento,
                estado=estado,
                errores=0 if mensaje is None else 1,
                mensaje_error=mensaje,
            )
        )
    sesion.flush()

    ejecucion = por_nombre(cliente.get("/salud").json())["Tienda A"]["ultima_ejecucion"]

    assert ejecucion["estado"] == "fallida"
    assert ejecucion["mensaje_error"] == "la tienda no respondió"


def test_sin_base_de_datos_responde_503(cliente: TestClient) -> None:
    class SesionCaida:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("sin conexión"))

    app.dependency_overrides[obtener_sesion] = lambda: SesionCaida()

    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 503
    assert respuesta.json() == {
        "estado": "degradado",
        "base_de_datos": "sin_conexion",
        "plataformas": [],
    }
