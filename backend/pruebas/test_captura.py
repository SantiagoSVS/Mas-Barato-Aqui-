"""Pruebas de integración de la captura: servicio por plataforma y pasada del worker."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.extraccion.servicio_captura import capturar_plataforma
from app.modelos import Captura, EjecucionCaptura, Oferta, Plataforma
from app.worker.capturas import ejecutar_capturas
from pruebas.falsos import ConectorFalso, ConectorRoto, ProveedorTasaFalso, oferta

MOMENTO = datetime(2026, 10, 31, 10, 0, tzinfo=UTC)


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

    ejecucion = capturar_plataforma(sesion, tienda, conector, ["celular"], ProveedorTasaFalso(None), lambda: MOMENTO)

    assert ejecucion.estado == "exitosa"
    assert ejecucion.ofertas_capturadas == 2
    assert ejecucion.errores == 0
    captura = sesion.scalar(select(Captura).join(Oferta).where(Oferta.url_origen == "https://t.example/1"))
    assert (captura.precio_cop, captura.envio_cop, captura.dias_entrega) == (789000, 0, 5)
    assert captura.capturado_en == MOMENTO


def test_una_segunda_pasada_agrega_historial_sin_duplicar_ofertas(sesion: Session) -> None:
    tienda = plataforma(sesion)
    for precio in ("789000", "779000"):
        conector = ConectorFalso({"celular": [oferta("https://t.example/1", precio)]})
        capturar_plataforma(sesion, tienda, conector, ["celular"], ProveedorTasaFalso(None))

    assert contar(sesion, Oferta) == 1
    precios = sesion.scalars(select(Captura.precio_cop).order_by(Captura.id)).all()
    assert precios == [789000, 779000]


def test_la_misma_publicacion_en_dos_terminos_se_captura_una_vez(sesion: Session) -> None:
    tienda = plataforma(sesion)
    repetida = oferta("https://t.example/1", "100000")
    conector = ConectorFalso({"celular": [repetida], "celular samsung": [repetida]})

    ejecucion = capturar_plataforma(
        sesion, tienda, conector, ["celular", "celular samsung"], ProveedorTasaFalso(None)
    )

    assert ejecucion.ofertas_capturadas == 1
    assert contar(sesion, Captura) == 1


def test_si_un_termino_falla_la_ejecucion_es_parcial(sesion: Session) -> None:
    tienda = plataforma(sesion)
    conector = ConectorFalso({"celular": [oferta("https://t.example/1", "100000")]}, fallas={"portátil"})

    ejecucion = capturar_plataforma(sesion, tienda, conector, ["celular", "portátil"], ProveedorTasaFalso(None))

    assert ejecucion.estado == "parcial"
    assert ejecucion.ofertas_capturadas == 1
    assert "la tienda no respondió" in ejecucion.mensaje_error


def test_si_todos_los_terminos_fallan_la_ejecucion_es_fallida(sesion: Session) -> None:
    tienda = plataforma(sesion)
    conector = ConectorFalso({}, fallas={"celular"})

    ejecucion = capturar_plataforma(sesion, tienda, conector, ["celular"], ProveedorTasaFalso(None))

    assert ejecucion.estado == "fallida"
    assert ejecucion.terminada_en is not None


def test_ofertas_en_dolares_guardan_precio_original_y_tasa(sesion: Session) -> None:
    tienda = plataforma(sesion, moneda="USD")
    conector = ConectorFalso({"celular": [oferta("https://usd.example/1", "183.75", moneda="USD", envio="15.50")]})
    proveedor = ProveedorTasaFalso(Decimal("4000"))

    capturar_plataforma(sesion, tienda, conector, ["celular"], proveedor)

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

    ejecucion = capturar_plataforma(sesion, tienda, conector, ["celular"], proveedor)

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

    ejecuciones = ejecutar_capturas(sesion, conectores, ["celular"], ProveedorTasaFalso(None))

    estados = {e.plataforma_id: e.estado for e in ejecuciones}
    assert estados == {rota.id: "fallida", sana.id: "exitosa"}
    fallida = sesion.scalar(select(EjecucionCaptura).where(EjecucionCaptura.plataforma_id == rota.id))
    assert "error inesperado del conector" in fallida.mensaje_error
    assert contar(sesion, Captura) == 1


def test_plataformas_inactivas_no_se_capturan(sesion: Session) -> None:
    inactiva = plataforma(sesion)
    inactiva.activa = False
    conectores = {"Tienda falsa": ConectorFalso({"celular": [oferta("https://t.example/1", "1")]})}

    assert ejecutar_capturas(sesion, conectores, ["celular"], ProveedorTasaFalso(None)) == []
