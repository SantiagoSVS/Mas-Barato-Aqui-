"""Pruebas de la migración inicial: tablas, índices y reglas que protegen los datos."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modelos import Captura, Oferta, Plataforma


def test_la_migracion_crea_las_seis_tablas(motor_pruebas: Engine) -> None:
    tablas = set(inspect(motor_pruebas).get_table_names())

    assert {"plataforma", "producto", "oferta", "captura", "consulta", "recomendacion"} <= tablas


def test_existen_los_indices_del_documento(motor_pruebas: Engine) -> None:
    inspector = inspect(motor_pruebas)
    indices_captura = {tuple(i["column_names"]) for i in inspector.get_indexes("captura")}
    indices_oferta = {tuple(i["column_names"]) for i in inspector.get_indexes("oferta")}

    assert ("oferta_id", "capturado_en") in indices_captura
    assert ("producto_id",) in indices_oferta


def _oferta_de_prueba(sesion: Session) -> Oferta:
    plataforma = Plataforma(
        nombre="Tienda USD", tipo_acceso="api", url_base="https://usd.example", moneda="USD"
    )
    oferta = Oferta(plataforma=plataforma, titulo_original="Producto", url_origen="https://usd.example/p")
    sesion.add(oferta)
    sesion.flush()
    return oferta


def test_captura_en_dolares_guarda_precio_original_y_tasa(sesion: Session) -> None:
    oferta = _oferta_de_prueba(sesion)
    captura = Captura(
        oferta=oferta,
        capturado_en=datetime(2026, 10, 31, tzinfo=UTC),
        precio_cop=1000,
        disponible=True,
        precio_original=Decimal("0.25"),
        moneda_original="USD",
        tasa_cambio=Decimal("4000.0000"),
    )
    sesion.add(captura)
    sesion.flush()

    assert captura.id is not None


def test_captura_en_dolares_sin_tasa_de_cambio_se_rechaza(sesion: Session) -> None:
    oferta = _oferta_de_prueba(sesion)
    sesion.add(
        Captura(
            oferta=oferta,
            capturado_en=datetime(2026, 10, 31, tzinfo=UTC),
            precio_cop=1000,
            disponible=True,
            precio_original=Decimal("0.25"),
            moneda_original="USD",
        )
    )

    with pytest.raises(IntegrityError):
        sesion.flush()


def test_precio_negativo_se_rechaza(sesion: Session) -> None:
    oferta = _oferta_de_prueba(sesion)
    sesion.add(
        Captura(
            oferta=oferta,
            capturado_en=datetime(2026, 10, 31, tzinfo=UTC),
            precio_cop=-1,
            disponible=True,
        )
    )

    with pytest.raises(IntegrityError):
        sesion.flush()


def test_plataforma_con_tipo_de_acceso_invalido_se_rechaza(sesion: Session) -> None:
    sesion.add(
        Plataforma(nombre="Tienda X", tipo_acceso="otro", url_base="https://x.example", moneda="COP")
    )

    with pytest.raises(IntegrityError):
        sesion.flush()
