"""POST /consultas, GET /productos, GET /productos/{id}/ofertas y GET /productos/{id}/historial (sección 5.6)."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import obtener_configuracion
from app.consultas.servicio import (
    Comparacion,
    ProductoResumen,
    RespuestaConsulta,
    comparar_producto,
    resolver_consulta,
)
from app.db import obtener_sesion
from app.historial.servicio import Historial, Periodo, construir_historial
from app.interpretacion.esquema import CriteriosConsulta, Prioridad
from app.interpretacion.interprete import ErrorConsulta, Interprete
from app.interpretacion.proveedor import ErrorProveedor
from app.interpretacion.registro import crear_interprete
from app.limite import LimitadorPorIp, cupo_del_modelo_agotado
from app.modelos import Producto

router = APIRouter(tags=["consultas"])


@lru_cache
def obtener_interprete() -> Interprete:
    return crear_interprete(obtener_configuracion())


@lru_cache
def obtener_limitador() -> LimitadorPorIp:
    return LimitadorPorIp(obtener_configuracion().limite_consultas_por_minuto)


class ConsultaEntrada(BaseModel):
    # El límite real (300) lo aplica el intérprete; este solo evita cuerpos enormes
    texto: str = Field(min_length=1, max_length=2000)
    # Criterio elegido en P3 (RF-11); si no viene, se usa el que interpretó el modelo
    prioridad: Prioridad | None = None
    # Criterios corregidos por el usuario en P2; si vienen, no se llama al modelo de lenguaje
    criterios: CriteriosConsulta | None = None


@router.post("/consultas", response_model=RespuestaConsulta)
def crear_consulta(
    entrada: ConsultaEntrada,
    peticion: Request,
    sesion: Annotated[Session, Depends(obtener_sesion)],
    interprete: Annotated[Interprete, Depends(obtener_interprete)],
    limitador: Annotated[LimitadorPorIp, Depends(obtener_limitador)],
) -> RespuestaConsulta:
    ip = peticion.client.host if peticion.client else "desconocida"
    if not limitador.permitir(ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Hiciste muchas consultas seguidas. Intenta de nuevo en un minuto."
        )
    # Con criterios editados no se llama al modelo, así que no gastan el cupo
    limite_diario = obtener_configuracion().limite_consultas_modelo_por_dia
    if entrada.criterios is None and cupo_del_modelo_agotado(sesion, limite_diario):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Se alcanzó el límite de búsquedas de hoy. Intenta de nuevo mañana."
        )
    try:
        return resolver_consulta(
            sesion, interprete, entrada.texto, entrada.prioridad, obtener_configuracion(), entrada.criterios
        )
    except ErrorConsulta as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except ErrorProveedor as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "No se pudo interpretar la consulta en este momento"
        ) from error


@router.get("/productos", response_model=list[ProductoResumen])
def listar_productos(sesion: Annotated[Session, Depends(obtener_sesion)]) -> list[ProductoResumen]:
    """Productos del catálogo, para sugerirlos cuando la consulta es ambigua."""
    productos = sesion.scalars(select(Producto).order_by(Producto.nombre_canonico))
    return [ProductoResumen(id=p.id, nombre=p.nombre_canonico) for p in productos]


@router.get("/productos/{producto_id}/ofertas", response_model=Comparacion)
def ofertas_de_producto(
    producto_id: int,
    sesion: Annotated[Session, Depends(obtener_sesion)],
    prioridad: Prioridad = "costo_total",
    presupuesto_cop: Annotated[int | None, Query(gt=0)] = None,
) -> Comparacion:
    producto = sesion.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El producto no existe")
    comparacion, _ = comparar_producto(sesion, producto, prioridad, presupuesto_cop, obtener_configuracion())
    return comparacion


@router.get("/productos/{producto_id}/historial", response_model=Historial)
def historial_de_producto(
    producto_id: int,
    sesion: Annotated[Session, Depends(obtener_sesion)],
    periodo: Periodo = "3M",
) -> Historial:
    producto = sesion.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El producto no existe")
    return construir_historial(sesion, producto, periodo, obtener_configuracion().historial_umbral_cercania)
