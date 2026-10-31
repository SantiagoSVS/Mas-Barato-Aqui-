"""Una pasada de captura por todas las plataformas activas.

Cada plataforma se procesa y se guarda por separado: si una falla, su error queda registrado
y el worker sigue con las demás (RNF-05).
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.extraccion.conector import Conector
from app.extraccion.servicio_captura import LARGO_MAXIMO_MENSAJE, capturar_plataforma
from app.extraccion.tasa_cambio import ProveedorTasaCambio
from app.modelos import EjecucionCaptura, Plataforma

log = logging.getLogger(__name__)


def ejecutar_capturas(
    sesion: Session,
    conectores: dict[str, Conector],
    terminos: list[str],
    proveedor_tasa: ProveedorTasaCambio,
    ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> list[EjecucionCaptura]:
    plataformas = sesion.scalars(
        select(Plataforma).where(Plataforma.activa).order_by(Plataforma.nombre)
    ).all()

    ejecuciones: list[EjecucionCaptura] = []
    for plataforma in plataformas:
        conector = conectores.get(plataforma.nombre)
        if conector is None:
            log.warning("%s está activa pero no tiene conector; se omite", plataforma.nombre)
            continue

        try:
            ejecucion = capturar_plataforma(sesion, plataforma, conector, terminos, proveedor_tasa, ahora)
            sesion.commit()
        except Exception as error:  # noqa: BLE001  (cualquier falla de una tienda se aísla)
            sesion.rollback()
            log.exception("Falló la captura de %s", plataforma.nombre)
            ejecucion = _registrar_falla(sesion, plataforma, error, ahora)

        log.info(
            "%s: %s, %d ofertas, %d errores",
            plataforma.nombre,
            ejecucion.estado,
            ejecucion.ofertas_capturadas,
            ejecucion.errores,
        )
        ejecuciones.append(ejecucion)
    return ejecuciones


def _registrar_falla(
    sesion: Session, plataforma: Plataforma, error: Exception, ahora: Callable[[], datetime]
) -> EjecucionCaptura:
    """Guarda una ejecución fallida cuando el error ocurrió fuera del manejo normal."""
    momento = ahora()
    ejecucion = EjecucionCaptura(
        plataforma=plataforma,
        iniciada_en=momento,
        terminada_en=momento,
        estado="fallida",
        ofertas_capturadas=0,
        errores=1,
        mensaje_error=f"{type(error).__name__}: {error}"[:LARGO_MAXIMO_MENSAJE],
    )
    sesion.add(ejecucion)
    sesion.commit()
    return ejecucion
