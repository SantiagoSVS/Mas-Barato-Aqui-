"""Una oferta que dejó de capturarse no compite con un precio viejo; su historial se conserva."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Configuracion
from app.consultas.busqueda import ofertas_vigentes
from app.consultas.servicio import comparar_producto
from app.historial.servicio import construir_historial
from app.interpretacion.esquema import Prioridad
from app.modelos import Captura, Oferta, Plataforma, Producto

CONFIG = Configuracion(database_url="postgresql+psycopg://x@localhost/x", oferta_vigencia_dias=3)
COSTO_TOTAL: Prioridad = "costo_total"


@pytest.fixture
def producto(sesion: Session) -> Producto:
    nuevo = Producto(nombre_canonico="Producto de prueba", categoria="hogar")
    sesion.add(nuevo)
    sesion.flush()
    return nuevo


def capturar(sesion: Session, producto: Producto, tienda: str, precio: int, hace: timedelta) -> None:
    plataforma = sesion.scalar(select(Plataforma).where(Plataforma.nombre == tienda))
    oferta = Oferta(plataforma=plataforma, producto=producto, titulo_original="x", url_origen=f"https://ejemplo/{tienda}/{precio}")
    sesion.add(oferta)
    sesion.add(
        Captura(oferta=oferta, capturado_en=datetime.now(UTC) - hace, precio_cop=precio, envio_cop=0, dias_entrega=2, disponible=True)
    )
    sesion.flush()


def test_sin_plazo_no_filtra(sesion: Session, producto: Producto) -> None:
    capturar(sesion, producto, "Mercado Libre", 100_000, timedelta(days=30))
    assert len(ofertas_vigentes(sesion, producto.id)) == 1


def test_respeta_el_plazo(sesion: Session, producto: Producto) -> None:
    capturar(sesion, producto, "Mercado Libre", 100_000, timedelta(days=2, hours=23))
    capturar(sesion, producto, "Mercado Libre", 90_000, timedelta(days=3, hours=1))
    assert [o.precio_cop for o in ofertas_vigentes(sesion, producto.id, 3)] == [100_000]


def test_una_oferta_vieja_mas_barata_no_es_la_recomendada(sesion: Session, producto: Producto) -> None:
    capturar(sesion, producto, "Mercado Libre", 90_000, timedelta(days=10))
    capturar(sesion, producto, "Mercado Libre", 100_000, timedelta(hours=1))

    comparacion, _ = comparar_producto(sesion, producto, COSTO_TOTAL, None, CONFIG)

    assert comparacion.recomendada.costo_total_cop == 100_000
    assert comparacion.alternativas == []


def test_una_captura_nueva_devuelve_la_oferta(sesion: Session, producto: Producto) -> None:
    capturar(sesion, producto, "Mercado Libre", 100_000, timedelta(days=10))
    oferta = sesion.scalar(select(Oferta).where(Oferta.producto_id == producto.id))
    sesion.add(
        Captura(oferta=oferta, capturado_en=datetime.now(UTC), precio_cop=110_000, envio_cop=0, dias_entrega=2, disponible=True)
    )
    sesion.flush()

    assert [o.precio_cop for o in ofertas_vigentes(sesion, producto.id, 3)] == [110_000]


def test_sin_ofertas_recientes_avisa_y_no_afirma_que_las_tiendas_no_lo_tengan(sesion: Session, producto: Producto) -> None:
    capturar(sesion, producto, "Mercado Libre", 100_000, timedelta(days=10))

    comparacion, _ = comparar_producto(sesion, producto, COSTO_TOTAL, None, CONFIG)

    assert comparacion.recomendada is None
    assert comparacion.tiendas.sin_producto == []
    assert any("precios recientes" in a for a in comparacion.avisos)


def test_una_tienda_sin_oferta_reciente_cuenta_como_sin_producto(sesion: Session, producto: Producto) -> None:
    capturar(sesion, producto, "Mercado Libre", 100_000, timedelta(days=10))
    capturar(sesion, producto, "Homecenter", 120_000, timedelta(hours=1))

    comparacion, _ = comparar_producto(sesion, producto, COSTO_TOTAL, None, CONFIG)

    assert comparacion.tiendas.con_resultados == ["Homecenter"]
    assert "Mercado Libre" in comparacion.tiendas.sin_producto
    assert not any("precios recientes" in a for a in comparacion.avisos)


def test_el_historial_conserva_la_serie_pero_no_da_precio_actual_viejo(sesion: Session, producto: Producto) -> None:
    capturar(sesion, producto, "Mercado Libre", 100_000, timedelta(days=10))

    historial = construir_historial(sesion, producto, "1M", 0.05, dias_vigencia=3)

    assert [s.plataforma for s in historial.series] == ["Mercado Libre"]
    assert historial.resumen[0].precio_actual_cop is None
    assert historial.resumen[0].minimo_periodo_cop == 100_000
    assert historial.indicador is None
