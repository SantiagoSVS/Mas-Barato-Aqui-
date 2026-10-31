"""Captura de una plataforma: pide las ofertas al conector, las normaliza y las guarda.

Cada pasada queda registrada en ejecucion_captura con su estado y sus errores. Las capturas
nunca se sobrescriben: cada pasada agrega un punto al historial de cada oferta.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.extraccion.conector import Conector, ErrorConector
from app.extraccion.normalizacion import ErrorNormalizacion, normalizar_oferta
from app.extraccion.tasa_cambio import ProveedorTasaCambio, TasaCambio
from app.extraccion.tipos import OfertaCapturada, OfertaNormalizada
from app.modelos import Captura, EjecucionCaptura, Oferta, Plataforma

# Límite de caracteres del mensaje de error guardado, para que un error enorme no llene la tabla
LARGO_MAXIMO_MENSAJE = 2000


def capturar_plataforma(
    sesion: Session,
    plataforma: Plataforma,
    conector: Conector,
    terminos: list[str],
    proveedor_tasa: ProveedorTasaCambio,
    ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> EjecucionCaptura:
    ejecucion = EjecucionCaptura(
        plataforma=plataforma, iniciada_en=ahora(), estado="en_curso", ofertas_capturadas=0, errores=0
    )
    sesion.add(ejecucion)
    sesion.flush()

    mensajes: list[str] = []
    tasas: dict[str, TasaCambio | None] = {}
    urls_guardadas: set[str] = set()
    terminos_fallidos = 0

    for termino in terminos:
        try:
            ofertas = conector.buscar(termino)
        except ErrorConector as error:
            terminos_fallidos += 1
            mensajes.append(f"[{termino}] {error}")
            continue

        for oferta in ofertas:
            try:
                normalizada = normalizar_oferta(oferta, _tasa_para(oferta, proveedor_tasa, tasas, ahora))
            except (ErrorNormalizacion, ErrorConector) as error:
                # Ante la duda, omitir: la oferta no se guarda y el motivo queda registrado
                ejecucion.errores += 1
                mensajes.append(f"[{termino}] {oferta.url}: {error}")
                continue
            # Dos términos pueden encontrar la misma publicación: se captura una sola vez
            if normalizada.url in urls_guardadas:
                continue
            _guardar(sesion, plataforma, normalizada, ahora())
            urls_guardadas.add(normalizada.url)
            ejecucion.ofertas_capturadas += 1

    ejecucion.errores += terminos_fallidos
    ejecucion.terminada_en = ahora()
    ejecucion.estado = _estado_final(len(terminos), terminos_fallidos, ejecucion.errores)
    ejecucion.mensaje_error = "\n".join(mensajes)[:LARGO_MAXIMO_MENSAJE] or None
    sesion.flush()
    return ejecucion


def _tasa_para(
    oferta: OfertaCapturada,
    proveedor: ProveedorTasaCambio,
    tasas: dict[str, TasaCambio | None],
    ahora: Callable[[], datetime],
) -> TasaCambio | None:
    """Tasa del día de la captura, pedida una sola vez por moneda en cada pasada.

    Si la consulta falla se recuerda como None, para no repetirla con cada oferta; sin tasa,
    normalizar_oferta rechaza las ofertas en esa moneda.
    """
    if oferta.moneda == "COP":
        return None
    if oferta.moneda not in tasas:
        try:
            tasas[oferta.moneda] = proveedor.obtener(oferta.moneda, ahora().date())
        except ErrorConector:
            tasas[oferta.moneda] = None
            raise
    return tasas[oferta.moneda]


def _guardar(sesion: Session, plataforma: Plataforma, datos: OfertaNormalizada, momento: datetime) -> None:
    """Crea la oferta si es nueva (por plataforma + URL) y le agrega una captura."""
    oferta = sesion.scalar(
        select(Oferta).where(Oferta.plataforma_id == plataforma.id, Oferta.url_origen == datos.url)
    )
    if oferta is None:
        oferta = Oferta(plataforma=plataforma, url_origen=datos.url, titulo_original=datos.titulo)
        sesion.add(oferta)
        sesion.flush()
    oferta.titulo_original = datos.titulo
    oferta.vendedor = datos.vendedor

    sesion.add(
        Captura(
            oferta=oferta,
            capturado_en=momento,
            precio_cop=datos.precio_cop,
            envio_cop=datos.envio_cop,
            dias_entrega=datos.dias_entrega,
            disponible=datos.disponible,
            precio_original=datos.precio_original,
            moneda_original=datos.moneda_original,
            tasa_cambio=datos.tasa_cambio,
        )
    )


def _estado_final(total_terminos: int, terminos_fallidos: int, errores: int) -> str:
    if total_terminos > 0 and terminos_fallidos == total_terminos:
        return "fallida"
    if errores > 0:
        return "parcial"
    return "exitosa"
