"""Historial de precios de un producto, a partir de las capturas (que nunca se sobrescriben).

Para la pantalla P4:

- Serie por tienda: el precio más bajo del producto en cada tienda, por día (hora de Colombia).
  Una tienda puede tener varias publicaciones (vendedores); su línea muestra el menor precio de
  ese día. Es el precio del producto sin envío, como dice la nota de P4.
- Resumen por tienda: precio actual (última captura de cada publicación) y mínimo del periodo.
- Indicador "Cerca de su mínimo histórico" (RF-10) para la tienda recomendada: el precio actual
  no supera el mínimo del periodo en más del umbral configurado.

Solo cuentan las capturas con el producto disponible y las tiendas activas.
"""

from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.consultas.busqueda import ofertas_vigentes
from app.costo.motor import formato_pesos, ordenar
from app.modelos import Captura, Oferta, Plataforma, Producto

ZONA_COLOMBIA = ZoneInfo("America/Bogota")
Periodo = Literal["1M", "3M", "6M"]
DIAS_POR_PERIODO = {"1M": 30, "3M": 90, "6M": 180}
NOMBRE_PERIODO = {"1M": "1 mes", "3M": "3 meses", "6M": "6 meses"}
NOTA = "Precio del producto sin envío."
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]


class PuntoSerie(BaseModel):
    fecha: date
    precio_min_cop: int


class SerieTienda(BaseModel):
    plataforma: str
    puntos: list[PuntoSerie]


class ResumenTienda(BaseModel):
    plataforma: str
    precio_actual_cop: int | None  # None si hoy no tiene publicaciones disponibles
    minimo_periodo_cop: int
    fecha_minimo: date
    en_su_minimo: bool


class Indicador(BaseModel):
    plataforma: str
    precio_actual_cop: int
    minimo_periodo_cop: int
    diferencia_cop: int
    cerca_del_minimo: bool
    mensaje: str


class Historial(BaseModel):
    producto_id: int
    producto: str
    periodo: Periodo
    desde: date
    hasta: date
    # Primer día con datos dentro del periodo. Si es posterior a "desde", el historial todavía no
    # cubre todo el periodo y los mensajes no hablan de "3 meses" sino "desde el <día>".
    datos_desde: date | None
    series: list[SerieTienda]
    resumen: list[ResumenTienda]
    indicador: Indicador | None
    ultima_captura: datetime | None
    nota: str = NOTA


def serie_por_tienda(sesion: Session, producto_id: int, desde: date) -> dict[str, list[PuntoSerie]]:
    dia = cast(func.timezone("America/Bogota", Captura.capturado_en), Date)
    filas = sesion.execute(
        select(Plataforma.nombre, dia, func.min(Captura.precio_cop))
        .join(Oferta, Oferta.plataforma_id == Plataforma.id)
        .join(Captura, Captura.oferta_id == Oferta.id)
        .where(Oferta.producto_id == producto_id, Plataforma.activa, Captura.disponible, dia >= desde)
        .group_by(Plataforma.nombre, dia)
        .order_by(Plataforma.nombre, dia)
    ).all()
    series: dict[str, list[PuntoSerie]] = {}
    for plataforma, fecha, precio in filas:
        series.setdefault(plataforma, []).append(PuntoSerie(fecha=fecha, precio_min_cop=precio))
    return series


def construir_historial(
    sesion: Session,
    producto: Producto,
    periodo: Periodo,
    umbral_cercania: float,
    hoy: date | None = None,
    dias_vigencia: int | None = None,
) -> Historial:
    hoy = hoy or datetime.now(ZONA_COLOMBIA).date()
    desde = hoy - timedelta(days=DIAS_POR_PERIODO[periodo])
    series = serie_por_tienda(sesion, producto.id, desde)

    vigentes = [o for o in ofertas_vigentes(sesion, producto.id, dias_vigencia) if o.disponible]
    precio_actual: dict[str, int] = {}
    for oferta in vigentes:
        precio_actual[oferta.plataforma] = min(oferta.precio_cop, precio_actual.get(oferta.plataforma, oferta.precio_cop))

    resumen = []
    for plataforma, puntos in series.items():
        minimo = min(puntos, key=lambda p: (p.precio_min_cop, p.fecha))
        actual = precio_actual.get(plataforma)
        resumen.append(
            ResumenTienda(
                plataforma=plataforma,
                precio_actual_cop=actual,
                minimo_periodo_cop=minimo.precio_min_cop,
                fecha_minimo=minimo.fecha,
                en_su_minimo=actual is not None and actual <= minimo.precio_min_cop,
            )
        )

    datos_desde = min((p.fecha for puntos in series.values() for p in puntos), default=None)
    return Historial(
        producto_id=producto.id,
        producto=producto.nombre_canonico,
        periodo=periodo,
        desde=desde,
        hasta=hoy,
        datos_desde=datos_desde,
        series=[SerieTienda(plataforma=p, puntos=puntos) for p, puntos in series.items()],
        resumen=resumen,
        indicador=_indicador(vigentes, resumen, _plazo(periodo, desde, datos_desde), umbral_cercania),
        ultima_captura=max((o.capturado_en for o in vigentes), default=None),
    )


def _plazo(periodo: Periodo, desde: date, datos_desde: date | None) -> str:
    """Cómo nombrar el periodo sin exagerar: "de 3 meses" solo si hay datos de todo el periodo."""
    if datos_desde is not None and datos_desde > desde:
        return f"desde el {datos_desde.day} de {MESES[datos_desde.month - 1]}"
    return f"de {NOMBRE_PERIODO[periodo]}"


def _indicador(vigentes, resumen: list[ResumenTienda], plazo: str, umbral: float) -> Indicador | None:
    """Indicador para la tienda de la oferta recomendada (menor costo total)."""
    recomendada = ordenar(vigentes, w=0).recomendada
    if recomendada is None:
        return None
    tienda = next((r for r in resumen if r.plataforma == recomendada.oferta.plataforma), None)
    if tienda is None or tienda.precio_actual_cop is None:
        return None

    diferencia = tienda.precio_actual_cop - tienda.minimo_periodo_cop
    cerca = tienda.precio_actual_cop <= tienda.minimo_periodo_cop * (1 + umbral)
    if diferencia <= 0:
        mensaje = f"En {tienda.plataforma}, la opción recomendada, está en su precio más bajo {plazo}."
    else:
        mensaje = (
            f"En {tienda.plataforma}, la opción recomendada, está a {formato_pesos(diferencia)} "
            f"del mínimo {plazo}."
        )
    return Indicador(
        plataforma=tienda.plataforma,
        precio_actual_cop=tienda.precio_actual_cop,
        minimo_periodo_cop=tienda.minimo_periodo_cop,
        diferencia_cop=diferencia,
        cerca_del_minimo=cerca,
        mensaje=mensaje,
    )
