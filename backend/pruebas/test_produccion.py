"""Pruebas de la unión de API e interfaz en producción y de la protección de los créditos."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Configuracion, obtener_configuracion
from app.db import obtener_sesion
from app.interpretacion.interprete import Interprete
from app.interpretacion.proveedor_falso import ProveedorFalso
from app.limite import cupo_del_modelo_agotado
from app.main import app
from app.modelos import Consulta
from app.produccion import crear_sitio
from app.rutas.consultas import obtener_interprete


@pytest.fixture
def sitio(tmp_path: Path, sesion: Session) -> Iterator[TestClient]:
    (tmp_path / "index.html").write_text("<title>Mas Barato</title>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    app.dependency_overrides[obtener_sesion] = lambda: sesion
    yield TestClient(crear_sitio(tmp_path))
    app.dependency_overrides.clear()


def test_la_api_queda_bajo_api(sitio: TestClient) -> None:
    respuesta = sitio.get("/api/productos")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("application/json")


def test_la_raiz_entrega_la_interfaz(sitio: TestClient) -> None:
    assert "Mas Barato" in sitio.get("/").text


@pytest.mark.parametrize("ruta", ["/resultados", "/productos/5/historial", "/sin-cobertura"])
def test_las_pantallas_entregan_la_interfaz_al_recargar(sitio: TestClient, ruta: str) -> None:
    respuesta = sitio.get(ruta)
    assert respuesta.status_code == 200
    assert "Mas Barato" in respuesta.text


def test_entrega_los_archivos_y_no_oculta_los_que_faltan(sitio: TestClient) -> None:
    assert sitio.get("/assets/app.js").text == "console.log(1)"
    assert sitio.get("/assets/no-existe.js").status_code == 404


def test_una_ruta_inexistente_de_la_api_no_entrega_la_interfaz(sitio: TestClient) -> None:
    assert sitio.get("/api/no-existe").status_code == 404


def consulta(sesion: Session, tokens: int | None, hace: timedelta = timedelta(hours=1)) -> None:
    sesion.add(Consulta(texto_original="x", tokens_consumidos=tokens, creada_en=datetime.now(UTC) - hace))
    sesion.flush()


def test_sin_cupo_configurado_nunca_se_agota(sesion: Session) -> None:
    consulta(sesion, 100)
    assert not cupo_del_modelo_agotado(sesion, None)


def test_el_cupo_cuenta_solo_llamadas_al_modelo_de_las_ultimas_24_horas(sesion: Session) -> None:
    consulta(sesion, 100)
    consulta(sesion, 0)  # criterios editados: no llamó al modelo
    consulta(sesion, None)
    consulta(sesion, 100, hace=timedelta(hours=25))
    assert not cupo_del_modelo_agotado(sesion, 2)
    consulta(sesion, 100)
    assert cupo_del_modelo_agotado(sesion, 2)


def test_con_el_cupo_agotado_no_se_llama_al_modelo(
    cliente: TestClient, sesion: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    consulta(sesion, 100)
    monkeypatch.setattr(obtener_configuracion(), "limite_consultas_modelo_por_dia", 1)
    app.dependency_overrides[obtener_interprete] = lambda: Interprete(ProveedorFalso(), 0.5)

    respuesta = cliente.post("/consultas", json={"texto": "celular samsung"})

    assert respuesta.status_code == 429
    assert "hoy" in respuesta.json()["detail"]


@pytest.mark.parametrize("prefijo", ["postgresql://", "postgres://"])
def test_acepta_la_direccion_tal_como_la_entrega_neon(prefijo: str) -> None:
    configuracion = Configuracion(database_url=f"{prefijo}u:c@ep.neon.tech/neondb?sslmode=require")
    assert configuracion.database_url == "postgresql+psycopg://u:c@ep.neon.tech/neondb?sslmode=require"


def test_no_cambia_una_direccion_que_ya_indica_el_controlador() -> None:
    url = "postgresql+psycopg://u:c@localhost/x"
    assert Configuracion(database_url=url).database_url == url
