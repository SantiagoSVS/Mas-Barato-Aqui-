"""Pruebas del historial de precios (RF-09, RF-10). Los precios son datos de prueba."""

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.historial.servicio import construir_historial
from app.modelos import Captura, Oferta, Plataforma, Producto

HOY = date(2026, 11, 2)


def en_utc(dia: date, hora: int = 15) -> datetime:
    return datetime(dia.year, dia.month, dia.day, hora, tzinfo=UTC)


def plataforma(sesion: Session, nombre: str) -> Plataforma:
    return sesion.scalar(select(Plataforma).where(Plataforma.nombre == nombre))


def capturar(sesion, producto, tienda, url, momento, precio, envio=0, dias=3, disponible=True) -> None:
    oferta = sesion.scalar(select(Oferta).where(Oferta.url_origen == url))
    if oferta is None:
        oferta = Oferta(plataforma=plataforma(sesion, tienda), producto=producto, titulo_original="x", url_origen=url)
        sesion.add(oferta)
    sesion.add(
        Captura(oferta=oferta, capturado_en=momento, precio_cop=precio, envio_cop=envio, dias_entrega=dias, disponible=disponible)
    )
    sesion.flush()


def producto(sesion: Session) -> Producto:
    nuevo = Producto(nombre_canonico="Reloj X", categoria="tecnologia")
    sesion.add(nuevo)
    sesion.flush()
    return nuevo


def test_serie_por_tienda_toma_el_menor_precio_de_cada_dia(sesion: Session) -> None:
    reloj = producto(sesion)
    ayer = HOY - timedelta(days=1)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(ayer), 150_000)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/2", en_utc(ayer), 145_000)  # otro vendedor, más barato
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY), 149_000)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/2", en_utc(HOY), 152_000)

    historial = construir_historial(sesion, reloj, "3M", 0.05, hoy=HOY)

    [serie] = historial.series
    assert serie.plataforma == "Mercado Libre"
    assert [(p.fecha, p.precio_min_cop) for p in serie.puntos] == [(ayer, 145_000), (HOY, 149_000)]


def test_el_dia_se_cuenta_en_hora_de_colombia(sesion: Session) -> None:
    reloj = producto(sesion)
    # 2 de noviembre a las 03:00 UTC son las 22:00 del 1 de noviembre en Colombia
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", datetime(2026, 11, 2, 3, tzinfo=UTC), 100_000)

    historial = construir_historial(sesion, reloj, "1M", 0.05, hoy=HOY)

    assert historial.series[0].puntos[0].fecha == date(2026, 11, 1)


def test_excluye_no_disponibles_tiendas_inactivas_y_fuera_del_periodo(sesion: Session) -> None:
    reloj = producto(sesion)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY), 150_000)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/2", en_utc(HOY), 90_000, disponible=False)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY - timedelta(days=40)), 80_000)  # fuera de 1M
    capturar(sesion, reloj, "Homecenter", "https://hc/1", en_utc(HOY), 70_000)
    plataforma(sesion, "Homecenter").activa = False

    historial = construir_historial(sesion, reloj, "1M", 0.05, hoy=HOY)

    assert [(s.plataforma, [p.precio_min_cop for p in s.puntos]) for s in historial.series] == [("Mercado Libre", [150_000])]
    # Con 3 meses sí entra la captura de hace 40 días
    tres_meses = construir_historial(sesion, reloj, "3M", 0.05, hoy=HOY)
    assert tres_meses.resumen[0].minimo_periodo_cop == 80_000


def test_resumen_por_tienda(sesion: Session) -> None:
    reloj = producto(sesion)
    hace_10 = HOY - timedelta(days=10)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(hace_10), 139_000)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY), 149_000)
    capturar(sesion, reloj, "Falabella", "https://fal/1", en_utc(HOY), 159_900, envio=None, dias=None)

    resumen = {r.plataforma: r for r in construir_historial(sesion, reloj, "3M", 0.05, hoy=HOY).resumen}

    assert (resumen["Mercado Libre"].precio_actual_cop, resumen["Mercado Libre"].minimo_periodo_cop) == (149_000, 139_000)
    assert resumen["Mercado Libre"].fecha_minimo == hace_10
    assert not resumen["Mercado Libre"].en_su_minimo
    assert resumen["Falabella"].en_su_minimo


def test_indicador_cerca_del_minimo_como_en_el_mockup(sesion: Session) -> None:
    reloj = producto(sesion)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY - timedelta(days=90)), 800_000)  # cubre 3M
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY - timedelta(days=20)), 779_000)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY), 789_000)

    indicador = construir_historial(sesion, reloj, "3M", 0.05, hoy=HOY).indicador

    assert indicador.plataforma == "Mercado Libre"
    assert indicador.diferencia_cop == 10_000
    assert indicador.cerca_del_minimo  # 789.000 <= 779.000 · 1,05
    assert indicador.mensaje == "En Mercado Libre, la opción recomendada, está a $10.000 del mínimo de 3 meses."


def test_indicador_lejos_del_minimo(sesion: Session) -> None:
    reloj = producto(sesion)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY - timedelta(days=5)), 100_000)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY), 120_000)

    assert not construir_historial(sesion, reloj, "1M", 0.05, hoy=HOY).indicador.cerca_del_minimo


def test_indicador_en_su_precio_mas_bajo(sesion: Session) -> None:
    reloj = producto(sesion)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY - timedelta(days=30)), 120_000)  # cubre 1M
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY), 100_000)

    indicador = construir_historial(sesion, reloj, "1M", 0.05, hoy=HOY).indicador

    assert indicador.diferencia_cop == 0
    assert indicador.mensaje == "En Mercado Libre, la opción recomendada, está en su precio más bajo de 1 mes."


def test_con_poco_historial_no_dice_3_meses(sesion: Session) -> None:
    reloj = producto(sesion)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(date(2026, 11, 1)), 100_000)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", en_utc(HOY), 100_000)

    historial = construir_historial(sesion, reloj, "3M", 0.05, hoy=HOY)

    assert historial.datos_desde == date(2026, 11, 1)
    assert historial.indicador.mensaje == (
        "En Mercado Libre, la opción recomendada, está en su precio más bajo desde el 1 de noviembre."
    )


def test_sin_oferta_recomendada_no_hay_indicador(sesion: Session) -> None:
    reloj = producto(sesion)
    capturar(sesion, reloj, "Falabella", "https://fal/1", en_utc(HOY), 159_900, envio=None, dias=None)

    assert construir_historial(sesion, reloj, "3M", 0.05, hoy=HOY).indicador is None


def test_endpoint_de_historial(cliente: TestClient, sesion: Session) -> None:
    reloj = producto(sesion)
    capturar(sesion, reloj, "Mercado Libre", "https://ml/1", datetime.now(UTC) - timedelta(hours=1), 149_000)

    respuesta = cliente.get(f"/productos/{reloj.id}/historial", params={"periodo": "1M"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["periodo"] == "1M"
    assert cuerpo["resumen"][0]["precio_actual_cop"] == 149_000
    assert cuerpo["nota"] == "Precio del producto sin envío."


def test_endpoint_valida_periodo_y_producto(cliente: TestClient, sesion: Session) -> None:
    reloj = producto(sesion)

    assert cliente.get(f"/productos/{reloj.id}/historial", params={"periodo": "2A"}).status_code == 422
    assert cliente.get("/productos/999999/historial").status_code == 404
