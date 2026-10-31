"""GET /salud: estado del servicio y de la última captura por plataforma (sección 5.6)."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import obtener_sesion
from app.modelos import Captura, Oferta, Plataforma

router = APIRouter(tags=["salud"])


class EstadoPlataforma(BaseModel):
    nombre: str
    activa: bool
    ultima_captura: datetime | None


class EstadoServicio(BaseModel):
    estado: Literal["ok", "degradado"]
    base_de_datos: Literal["ok", "sin_conexion"]
    plataformas: list[EstadoPlataforma]


@router.get("/salud", response_model=EstadoServicio)
def consultar_salud(
    respuesta: Response, sesion: Annotated[Session, Depends(obtener_sesion)]
) -> EstadoServicio:
    # Última captura de cada plataforma; las que aún no tienen capturas salen con None
    consulta = (
        select(Plataforma.nombre, Plataforma.activa, func.max(Captura.capturado_en))
        .outerjoin(Oferta, Oferta.plataforma_id == Plataforma.id)
        .outerjoin(Captura, Captura.oferta_id == Oferta.id)
        .group_by(Plataforma.id)
        .order_by(Plataforma.nombre)
    )
    try:
        filas = sesion.execute(consulta).all()
    except SQLAlchemyError:
        respuesta.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return EstadoServicio(estado="degradado", base_de_datos="sin_conexion", plataformas=[])

    return EstadoServicio(
        estado="ok",
        base_de_datos="ok",
        plataformas=[
            EstadoPlataforma(nombre=nombre, activa=activa, ultima_captura=ultima)
            for nombre, activa, ultima in filas
        ],
    )
