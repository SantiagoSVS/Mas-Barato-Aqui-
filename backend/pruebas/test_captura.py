"""Pruebas de integración de la captura: servicio por plataforma y pasada del worker."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.extraccion.servicio_captura import capturar_plataforma
from app.modelos import Captura, EjecucionCaptura, Oferta, Plataforma, Producto
from app.worker.capturas import ejecutar_capturas
from pruebas.falsos import ConectorFalso, ConectorRoto, ProveedorTasaFalso, oferta, producto

MOMENTO = datetime(2026, 10, 31, 10, 0, tzinfo=UTC)
CELULAR = producto("celular")


def plataforma(sesion: Session, nombre: str = "Tienda falsa", moneda: str = "COP") -> Plataforma:
    nueva = Plataforma(nombre=nombre, tipo_acceso="api", url_base="https://t.example", moneda=moneda)
    sesion.add(nueva)
    sesion.flush()
    return nueva


def contar(sesion: Session, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


def test_captura_exitosa_guarda_ofertas_y_capturas(sesion: Session) -> None:
    tienda = plataforma(sesion)
    conector = ConectorFalso(
        {"celular": [oferta("https://t.example/1", "789000", envio="0", dias=5), oferta("https://t.example/2", "769000")]}
    )

    ejecucion = capturar_plataforma(sesion, tienda, conector, [CELULAR], ProveedorTasaFalso(None), lambda: MOMENTO)

    assert ejecucion.estado == "exitosa"
    assert ejecucion.ofertas_capturadas == 2
    assert ejecucion.errores == 0
    captura = sesion.scalar(select(Captura).join(Oferta).where(Oferta.url_origen == "https://t.example/1"))
    assert (captura.precio_cop, captura.envio_cop, captura.dias_entrega) == (789000, 0, 5)
    assert captura.capturado_en == MOMENTO


def test_las_ofertas_quedan_vinculadas_al_producto_del_catalogo(sesion: Session) -> None:
    tienda = plataforma(sesion)
    del_catalogo = producto("Freidora X 5 L", categoria="hogar")
    del_catalogo.marca = "Marca X"
    conector = ConectorFalso({"Freidora X 5 L": [oferta("https://t.example/1", "300000")]})

    capturar_plataforma(sesion, tienda, conector, [del_catalogo], ProveedorTasaFalso(None))

    guardada = sesion.scalar(select(Oferta))
    assert guardada.producto.nombre_canonico == "Freidora X 5 L"
    assert (guardada.producto.categoria, guardada.producto.marca) == ("hogar", "Marca X")


def test_productos_sin_ofertas_en_la_tienda_no_se_crean(sesion: Session) -> None:
    tienda = plataforma(sesion)

    ejecucion = capturar_plataforma(sesion, tienda, ConectorFalso({}), [CELULAR], ProveedorTasaFalso(None))

    assert ejecucion.estado == "exitosa"
    assert contar(sesion, Producto) == 0


def test_una_segunda_pasada_agrega_historial_sin_duplicar(sesion: Session) -> None:
    tienda = plataforma(sesion)
    for precio in ("789000", "779000"):
        conector = ConectorFalso({"celular": [oferta("https://t.example/1", precio)]})
        capturar_plataforma(sesion, tienda, conector, [CELULAR], ProveedorTasaFalso(None))

    assert contar(sesion, Oferta) == 1
    assert contar(sesion, Producto) == 1
    precios = sesion.scalars(select(Captura.precio_cop).order_by(Captura.id)).all()
    assert precios == [789000, 779000]


def test_la_misma_publicacion_en_dos_productos_se_captura_una_vez(sesion: Session) -> None:
    tienda = plataforma(sesion)
    repetida = oferta("https://t.example/1", "100000")
    conector = ConectorFalso({"celular": [repetida], "celular samsung": [repetida]})

    ejecucion = capturar_plataforma(
        sesion, tienda, conector, [CELULAR, producto("celular samsung")], ProveedorTasaFalso(None)
    )

    assert ejecucion.ofertas_capturadas == 1
    assert contar(sesion, Captura) == 1


def test_si_un_producto_falla_la_ejecucion_es_parcial(sesion: Session) -> None:
    tienda = plataforma(sesion)
    conector = ConectorFalso({"celular": [oferta("https://t.example/1", "100000")]}, fallas={"portátil"})

    ejecucion = capturar_plataforma(
        sesion, tienda, conector, [CELULAR, producto("portátil")], ProveedorTasaFalso(None)
    )

    assert ejecucion.estado == "parcial"
    assert ejecucion.ofertas_capturadas == 1
    assert "[portátil] la tienda no respondió" in ejecucion.mensaje_error


def test_si_todos_los_productos_fallan_la_ejecucion_es_fallida(sesion: Session) -> None:
    tienda = plataforma(sesion)
    conector = ConectorFalso({}, fallas={"celular"})

    ejecucion = capturar_plataforma(sesion, tienda, conector, [CELULAR], ProveedorTasaFalso(None))

    assert ejecucion.estado == "fallida"
    assert ejecucion.terminada_en is not None


def test_ofertas_en_dolares_guardan_precio_original_y_tasa(sesion: Session) -> None:
    tienda = plataforma(sesion, moneda="USD")
    conector = ConectorFalso({"celular": [oferta("https://usd.example/1", "183.75", moneda="USD", envio="15.50")]})
    proveedor = ProveedorTasaFalso(Decimal("4000"))

    capturar_plataforma(sesion, tienda, conector, [CELULAR], proveedor)

    captura = sesion.scalar(select(Captura))
    assert (captura.precio_cop, captura.envio_cop) == (735000, 62000)
    assert captura.precio_original == Decimal("183.75")
    assert captura.tasa_cambio == Decimal("4000")


def test_sin_tasa_de_cambio_las_ofertas_en_dolares_se_omiten(sesion: Session) -> None:
    tienda = plataforma(sesion, moneda="USD")
    conector = ConectorFalso(
        {"celular": [oferta("https://usd.example/1", "10", moneda="USD"), oferta("https://usd.example/2", "20", moneda="USD")]}
    )
    proveedor = ProveedorTasaFalso(None)

    ejecucion = capturar_plataforma(sesion, tienda, conector, [CELULAR], proveedor)

    assert ejecucion.estado == "parcial"
    assert ejecucion.errores == 2
    assert contar(sesion, Captura) == 0
    assert proveedor.consultas == 1  # no se insiste con cada oferta


def test_una_plataforma_caida_no_detiene_a_las_demas(sesion: Session) -> None:
    rota = plataforma(sesion, nombre="Tienda rota")
    sana = plataforma(sesion, nombre="Tienda sana")
    plataforma(sesion, nombre="Tienda sin conector")
    # En producción las plataformas ya existen; se confirman para que el rollback de la
    # plataforma que falla no las deshaga (al final la prueba igual deshace todo)
    sesion.commit()
    conectores = {
        "Tienda rota": ConectorRoto(),
        "Tienda sana": ConectorFalso({"celular": [oferta("https://t.example/1", "100000")]}),
    }

    ejecuciones = ejecutar_capturas(sesion, conectores, [CELULAR], ProveedorTasaFalso(None))

    estados = {e.plataforma_id: e.estado for e in ejecuciones}
    assert estados == {rota.id: "fallida", sana.id: "exitosa"}
    fallida = sesion.scalar(select(EjecucionCaptura).where(EjecucionCaptura.plataforma_id == rota.id))
    assert "error inesperado del conector" in fallida.mensaje_error
    assert contar(sesion, Captura) == 1


def test_plataformas_inactivas_no_se_capturan(sesion: Session) -> None:
    inactiva = plataforma(sesion)
    inactiva.activa = False
    conectores = {"Tienda falsa": ConectorFalso({"celular": [oferta("https://t.example/1", "1")]})}

    assert ejecutar_capturas(sesion, conectores, [CELULAR], ProveedorTasaFalso(None)) == []
