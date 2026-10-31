"""Fixtures compartidas: base de datos de pruebas y cliente HTTP de la API.

Las pruebas usan TEST_DATABASE_URL, nunca la base de desarrollo. Al inicio se recrea el
esquema con las migraciones (bajar a cero y subir de nuevo), y cada prueba corre dentro de
una transacción que se deshace al final, así ninguna prueba deja datos para la siguiente.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import obtener_configuracion
from app.db import obtener_sesion
from app.main import app

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture(scope="session")
def motor_pruebas() -> Iterator[Engine]:
    configuracion = obtener_configuracion()
    url = configuracion.test_database_url
    if not url:
        pytest.exit("Falta TEST_DATABASE_URL en .env (ver .env.example).")
    if url == configuracion.database_url:
        pytest.exit("TEST_DATABASE_URL no puede ser la misma base de desarrollo.")

    alembic_cfg = Config(str(ALEMBIC_INI))
    alembic_cfg.attributes["url_bd"] = url
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    motor = create_engine(url)
    yield motor
    motor.dispose()


@pytest.fixture
def sesion(motor_pruebas: Engine) -> Iterator[Session]:
    with motor_pruebas.connect() as conexion:
        transaccion = conexion.begin()
        with Session(bind=conexion, join_transaction_mode="create_savepoint") as sesion:
            yield sesion
        transaccion.rollback()


@pytest.fixture
def cliente(sesion: Session) -> Iterator[TestClient]:
    app.dependency_overrides[obtener_sesion] = lambda: sesion
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()
