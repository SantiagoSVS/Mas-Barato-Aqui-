"""GET /salud: estado del servicio y de la última captura por plataforma (sección 5.6)."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import obtener_sesion
from app.modelos import Captura, EjecucionCaptura, Oferta, Plataforma

router = APIRouter(tags=["salud"])


class UltimaEjecucion(BaseModel):
    estado: str
    iniciada_en: datetime
    terminada_en: datetime | None
    ofertas_capturadas: int
    errores: int
    mensaje_error: str | None


class EstadoPlataforma(BaseModel):
    nombre: str
    activa: bool
    ultima_captura: datetime | None
    ultima_ejecucion: UltimaEjecucion | None


class EstadoServicio(BaseModel):
    estado: Literal["ok", "degradado"]
    base_de_datos: Literal["ok", "sin_conexion"]
    plataformas: list[EstadoPlataforma]


@router.get("/salud", response_model=EstadoServicio)
def consultar_salud(
    respuesta: Response, sesion: Annotated[Session, Depends(obtener_sesion)]
) -> EstadoServicio:
    # Última captura de cada plataforma; las que aún no tienen capturas salen con None
    consulta_capturas = (
        select(Plataforma.id, Plataforma.nombre, Plataforma.activa, func.max(Captura.capturado_en))
        .outerjoin(Oferta, Oferta.plataforma_id == Plataforma.id)
        .outerjoin(Captura, Captura.oferta_id == Oferta.id)
        .group_by(Plataforma.id)
        .order_by(Plataforma.nombre)
    )
    # Ejecución más reciente de cada plataforma (DISTINCT ON de PostgreSQL)
    consulta_ejecuciones = (
        select(EjecucionCaptura)
        .ext(distinct_on(EjecucionCaptura.plataforma_id))
        .order_by(EjecucionCaptura.plataforma_id, EjecucionCaptura.iniciada_en.desc())
    )
    try:
        filas = sesion.execute(consulta_capturas).all()
        ejecuciones = {e.plataforma_id: e for e in sesion.scalars(consulta_ejecuciones)}
    except SQLAlchemyError:
        respuesta.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return EstadoServicio(estado="degradado", base_de_datos="sin_conexion", plataformas=[])

    return EstadoServicio(
        estado="ok",
        base_de_datos="ok",
        plataformas=[
            EstadoPlataforma(
                nombre=nombre,
                activa=activa,
                ultima_captura=ultima,
                ultima_ejecucion=_resumir(ejecuciones.get(plataforma_id)),
            )
            for plataforma_id, nombre, activa, ultima in filas
        ],
    )


def _resumir(ejecucion: EjecucionCaptura | None) -> UltimaEjecucion | None:
    if ejecucion is None:
        return None
    return UltimaEjecucion(
        estado=ejecucion.estado,
        iniciada_en=ejecucion.iniciada_en,
        terminada_en=ejecucion.terminada_en,
        ofertas_capturadas=ejecucion.ofertas_capturadas,
        errores=ejecucion.errores,
        mensaje_error=ejecucion.mensaje_error,
    )
