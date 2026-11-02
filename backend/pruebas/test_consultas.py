"""Pruebas de integración de la búsqueda y de POST /consultas y GET /productos/{id}/ofertas.

Usan la base de pruebas (con las plataformas que registran las migraciones) y el proveedor
falso del intérprete. Los precios son datos de prueba.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Configuracion
from app.consultas.busqueda import buscar_productos, ofertas_vigentes
from app.consultas.servicio import AVISO_W_SIN_CALIBRAR, comparar_producto
from app.interpretacion.esquema import CriteriosConsulta
from app.interpretacion.interprete import Interprete
from app.interpretacion.proveedor_falso import ProveedorFalso
from app.main import app
from app.modelos import Captura, Consulta, Oferta, Plataforma, Producto, Recomendacion
from app.rutas.consultas import obtener_interprete

AYER = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
HOY = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
CONFIG = Configuracion(database_url="postgresql+psycopg://x@localhost/x")


@pytest.fixture
def api(cliente: TestClient) -> Iterator[TestClient]:
    app.dependency_overrides[obtener_interprete] = lambda: Interprete(ProveedorFalso(), 0.5)
    yield cliente


def plataforma(sesion: Session, nombre: str) -> Plataforma:
    return sesion.scalar(select(Plataforma).where(Plataforma.nombre == nombre))


def producto(sesion: Session, nombre: str, marca: str | None, modelo: str | None = None) -> Producto:
    nuevo = Producto(nombre_canonico=nombre, marca=marca, modelo=modelo, categoria="hogar")
    sesion.add(nuevo)
    sesion.flush()
    return nuevo


def capturar(sesion, producto, tienda, url, precio, envio, dias, momento=HOY, disponible=True) -> Oferta:
    oferta = sesion.scalar(select(Oferta).where(Oferta.url_origen == url))
    if oferta is None:
        oferta = Oferta(plataforma=plataforma(sesion, tienda), producto=producto, titulo_original=producto.nombre_canonico, url_origen=url)
        sesion.add(oferta)
    sesion.add(Captura(oferta=oferta, capturado_en=momento, precio_cop=precio, envio_cop=envio, dias_entrega=dias, disponible=disponible))
    sesion.flush()
    return oferta


@pytest.fixture
def freidora(sesion: Session) -> Producto:
    oster = producto(sesion, "Freidora de aire Oster DiamondForce 4 litros manual", "Oster", "CKSTAF401MDF")
    capturar(sesion, oster, "Mercado Libre", "https://ml.example/1", 250_000, 0, 3, momento=AYER)
    capturar(sesion, oster, "Mercado Libre", "https://ml.example/1", 224_175, 0, 3)  # la vigente es la de hoy
    capturar(sesion, oster, "Mercado Libre", "https://ml.example/2", 230_000, 0, 1)
    capturar(sesion, oster, "Falabella", "https://fal.example/1", 199_900, None, None)  # envío desconocido
    plataforma(sesion, "Falabella").nota_envio = "Envío gratis desde $149.000 (no aplica a todo)."
    return oster


# --- Búsqueda ---

def criterios(**campos) -> CriteriosConsulta:
    return CriteriosConsulta(**{"confianza": 0.9, "requiere_aclaracion": False, **campos})


def test_busca_por_producto_y_filtra_por_marca(sesion: Session, freidora: Producto) -> None:
    imusa = producto(sesion, "Freidora de aire Imusa Easy Fry Max 5 litros", "Imusa")

    assert {e.producto for e in buscar_productos(sesion, criterios(producto="freidora de aire"), 80)} == {freidora, imusa}
    assert [e.producto for e in buscar_productos(sesion, criterios(producto="freidora de aire", marca="Oster"), 80)] == [freidora]
    assert buscar_productos(sesion, criterios(producto="tenis", marca="Adidas"), 80) == []


def test_sin_producto_no_busca(sesion: Session, freidora: Producto) -> None:
    assert buscar_productos(sesion, criterios(marca="Oster"), 80) == []


def test_ofertas_vigentes_toma_la_ultima_captura_y_solo_tiendas_activas(sesion: Session, freidora: Producto) -> None:
    plataforma(sesion, "Falabella").activa = False

    vigentes = {o.url: o.precio_cop for o in ofertas_vigentes(sesion, freidora.id)}

    assert vigentes == {"https://ml.example/1": 224_175, "https://ml.example/2": 230_000}


# --- POST /consultas ---

def test_consulta_con_resultados(api: TestClient, sesion: Session, freidora: Producto) -> None:
    respuesta = api.post("/consultas", json={"texto": "freidora de aire oster que no pase de 250 mil"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "resultados"
    comparacion = cuerpo["comparacion"]
    assert comparacion["producto"]["id"] == freidora.id
    assert comparacion["recomendada"]["url"] == "https://ml.example/1"
    assert comparacion["recomendada"]["costo_total_cop"] == 224_175
    assert comparacion["explicacion"] == "es $5.825 más barata que la siguiente opción al sumar el envío."
    assert [a["url"] for a in comparacion["alternativas"]] == ["https://ml.example/2"]
    # Falabella es más barata en precio, pero sin envío conocido no se mezcla ni se recomienda
    assert [o["plataforma"] for o in comparacion["sin_costo_completo"]] == ["Falabella"]
    assert comparacion["notas_envio"] == {"Falabella": "Envío gratis desde $149.000 (no aplica a todo)."}
    assert comparacion["tiendas"]["sin_producto"] == ["Homecenter"]
    assert comparacion["aviso_costo"].startswith("Costo estimado")


def test_la_consulta_y_las_recomendaciones_quedan_registradas(api: TestClient, sesion: Session, freidora: Producto) -> None:
    consulta_id = api.post("/consultas", json={"texto": "freidora de aire oster"}).json()["consulta_id"]

    consulta = sesion.get(Consulta, consulta_id)
    assert consulta.con_cobertura is True
    assert consulta.criterios["marca"] == "Oster"
    assert consulta.tiempo_respuesta_ms is not None
    recomendaciones = sesion.scalars(select(Recomendacion).where(Recomendacion.consulta_id == consulta_id).order_by(Recomendacion.posicion)).all()
    assert [r.costo_total_cop for r in recomendaciones] == [224_175, 230_000]
    assert recomendaciones[0].componentes["w"] == 0


def test_consulta_que_requiere_aclaracion_no_busca(api: TestClient, sesion: Session, freidora: Producto) -> None:
    cuerpo = api.post("/consultas", json={"texto": "algo bueno y barato"}).json()

    assert cuerpo["estado"] == "requiere_aclaracion"
    assert cuerpo["comparacion"] is None
    assert sesion.get(Consulta, cuerpo["consulta_id"]).con_cobertura is None


def test_producto_fuera_del_catalogo_queda_sin_cobertura(api: TestClient, sesion: Session, freidora: Producto) -> None:
    cuerpo = api.post("/consultas", json={"texto": "tenis adidas para correr talla 42"}).json()

    assert cuerpo["estado"] == "sin_cobertura"
    assert sesion.get(Consulta, cuerpo["consulta_id"]).con_cobertura is False


def test_varios_productos_parecidos_se_ofrecen_como_alternativa(api: TestClient, sesion: Session, freidora: Producto) -> None:
    imusa = producto(sesion, "Freidora de aire Imusa Easy Fry Max 5 litros", "Imusa")

    cuerpo = api.post("/consultas", json={"texto": "una freidora de aire"}).json()

    ids = {cuerpo["comparacion"]["producto"]["id"], *[p["id"] for p in cuerpo["otros_productos"]]}
    assert ids == {freidora.id, imusa.id}


def test_entrega_rapida_sin_w_calibrado_avisa(api: TestClient, freidora: Producto) -> None:
    cuerpo = api.post("/consultas", json={"texto": "freidora de aire oster", "prioridad": "entrega_rapida"}).json()

    assert cuerpo["comparacion"]["prioridad"] == "entrega_rapida"
    assert cuerpo["comparacion"]["w"] == 0
    assert AVISO_W_SIN_CALIBRAR in cuerpo["comparacion"]["avisos"]


def test_entrega_rapida_con_w_calibrado_prefiere_la_que_llega_antes(sesion: Session, freidora: Producto) -> None:
    configuracion = Configuracion(database_url="postgresql+psycopg://x@localhost/x", peso_dia_espera_cop=10_000)

    comparacion, _ = comparar_producto(sesion, freidora, "entrega_rapida", None, configuracion)

    # ml/2: 230.000 + 10.000·1 = 240.000 gana a ml/1: 224.175 + 10.000·3 = 254.175
    assert comparacion.recomendada.url == "https://ml.example/2"
    assert comparacion.recomendada.costo_ajustado_cop == 240_000


def test_aviso_de_presupuesto(sesion: Session, freidora: Producto) -> None:
    comparacion, _ = comparar_producto(sesion, freidora, "costo_total", 225_000, CONFIG)

    assert comparacion.recomendada.supera_presupuesto is False
    assert comparacion.alternativas[0].supera_presupuesto is True


def test_consulta_demasiado_larga_responde_422(api: TestClient) -> None:
    respuesta = api.post("/consultas", json={"texto": "a" * 301})

    assert respuesta.status_code == 422
    assert "300" in respuesta.json()["detail"]


# --- GET /productos/{id}/ofertas ---

def test_ofertas_de_un_producto(api: TestClient, freidora: Producto) -> None:
    respuesta = api.get(f"/productos/{freidora.id}/ofertas")

    assert respuesta.status_code == 200
    assert respuesta.json()["recomendada"]["costo_total_cop"] == 224_175


def test_producto_inexistente_responde_404(api: TestClient) -> None:
    assert api.get("/productos/999999/ofertas").status_code == 404
