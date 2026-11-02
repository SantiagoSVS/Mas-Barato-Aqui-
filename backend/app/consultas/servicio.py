"""Del texto del usuario a la recomendación, sobre datos ya capturados.

Flujo de POST /consultas:

1. El intérprete convierte el texto en criterios (el único paso con modelo de lenguaje).
2. Si los criterios requieren aclaración, se devuelven sin buscar (pantalla P2).
3. Se buscan los productos del catálogo que corresponden. Si no hay, la consulta queda
   registrada "sin cobertura" (RF-13): esas consultas son la lista para ampliar el catálogo.
4. Con las ofertas vigentes del producto, el motor calcula CT y CA y ordena (código propio).
5. Se guardan la consulta y las recomendaciones para las métricas (RF-12) y la trazabilidad.
"""

import time
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import Configuracion
from app.consultas.busqueda import buscar_productos, ofertas_vigentes, plataformas_activas
from app.costo.motor import OfertaCalculada, explicar, ordenar, url_de_compra
from app.interpretacion.esquema import CriteriosConsulta, Prioridad
from app.interpretacion.interprete import Interprete, limpiar_consulta
from app.modelos import Consulta, Producto, Recomendacion

AVISO_COSTO = (
    "Costo estimado: no incluye impuestos, descuentos por medio de pago ni promociones que la "
    "tienda aplica al pagar."
)
AVISO_W_SIN_CALIBRAR = (
    "El criterio \"Entrega más rápida\" aún no está calibrado; las ofertas se ordenaron por menor "
    "costo total."
)


class OfertaRespuesta(BaseModel):
    plataforma: str
    titulo: str
    vendedor: str | None
    precio_cop: int
    envio_cop: int | None
    dias_entrega: int | None
    costo_total_cop: int | None
    costo_ajustado_cop: int | None
    supera_presupuesto: bool
    capturado_en: datetime
    url: str


class ProductoResumen(BaseModel):
    id: int
    nombre: str


class Tiendas(BaseModel):
    consultadas: list[str]
    con_resultados: list[str]
    sin_producto: list[str]


class Comparacion(BaseModel):
    producto: ProductoResumen
    prioridad: Prioridad
    w: int
    recomendada: OfertaRespuesta | None
    explicacion: str | None
    alternativas: list[OfertaRespuesta]
    sin_costo_completo: list[OfertaRespuesta]  # envío o días desconocidos: no se ordenan con las demás
    tiendas: Tiendas
    notas_envio: dict[str, str]
    avisos: list[str]
    aviso_costo: str = AVISO_COSTO


class RespuestaConsulta(BaseModel):
    consulta_id: int
    estado: Literal["resultados", "requiere_aclaracion", "sin_cobertura"]
    criterios: CriteriosConsulta
    comparacion: Comparacion | None
    otros_productos: list[ProductoResumen]


def peso_para(prioridad: Prioridad, configuracion: Configuracion) -> tuple[int, list[str]]:
    """w del perfil elegido (RF-11) y los avisos que haya que mostrar."""
    if prioridad == "costo_total":
        return 0, []
    if configuracion.peso_dia_espera_cop is None:
        return 0, [AVISO_W_SIN_CALIBRAR]
    return configuracion.peso_dia_espera_cop, []


def _respuesta(calculada: OfertaCalculada) -> OfertaRespuesta:
    oferta = calculada.oferta
    return OfertaRespuesta(
        plataforma=oferta.plataforma,
        titulo=oferta.titulo,
        vendedor=oferta.vendedor,
        precio_cop=oferta.precio_cop,
        envio_cop=oferta.envio_cop,
        dias_entrega=oferta.dias_entrega,
        costo_total_cop=calculada.costo_total,
        costo_ajustado_cop=calculada.costo_ajustado,
        supera_presupuesto=calculada.supera_presupuesto,
        capturado_en=oferta.capturado_en,
        url=url_de_compra(oferta),
    )


def comparar_producto(
    sesion: Session,
    producto: Producto,
    prioridad: Prioridad,
    presupuesto_cop: int | None,
    configuracion: Configuracion,
) -> tuple[Comparacion, list[OfertaCalculada]]:
    """Ranking de las ofertas de un producto. También lo usa GET /productos/{id}/ofertas."""
    w, avisos = peso_para(prioridad, configuracion)
    ranking = ordenar(ofertas_vigentes(sesion, producto.id), w, presupuesto_cop)
    activas = plataformas_activas(sesion)
    con_resultados = sorted({c.oferta.plataforma for c in [*ranking.ordenadas, *ranking.incompletas]})

    if ranking.recomendada is None and ranking.incompletas:
        avisos.append("Ninguna oferta tiene precio y envío conocidos, por eso no hay una recomendada.")

    comparacion = Comparacion(
        producto=ProductoResumen(id=producto.id, nombre=producto.nombre_canonico),
        prioridad=prioridad,
        w=w,
        recomendada=_respuesta(ranking.recomendada) if ranking.recomendada else None,
        explicacion=explicar(ranking),
        alternativas=[_respuesta(c) for c in ranking.ordenadas[1:]],
        sin_costo_completo=[_respuesta(c) for c in ranking.incompletas],
        tiendas=Tiendas(
            consultadas=[p.nombre for p in activas],
            con_resultados=con_resultados,
            sin_producto=[p.nombre for p in activas if p.nombre not in con_resultados],
        ),
        notas_envio={p.nombre: p.nota_envio for p in activas if p.nota_envio and p.nombre in con_resultados},
        avisos=avisos,
    )
    return comparacion, ranking.ordenadas


def resolver_consulta(
    sesion: Session,
    interprete: Interprete,
    texto: str,
    prioridad_elegida: Prioridad | None,
    configuracion: Configuracion,
    criterios_editados: CriteriosConsulta | None = None,
) -> RespuestaConsulta:
    """Resuelve una consulta. Si el usuario corrigió los criterios en P2 (criterios_editados),
    se usan esos y no se llama al modelo de lenguaje: no consume tokens."""
    inicio = time.perf_counter()
    if criterios_editados is None:
        interpretacion = interprete.interpretar(texto)  # ErrorConsulta / ErrorProveedor suben a la API
        texto_limpio, criterios = interpretacion.consulta, interpretacion.criterios
        tokens = interpretacion.tokens_entrada + interpretacion.tokens_salida
    else:
        texto_limpio, tokens = limpiar_consulta(texto), 0
        # Criterios confirmados por el usuario: solo falta aclarar si no dijo qué producto busca
        criterios = criterios_editados.model_copy(
            update={"confianza": 1.0, "requiere_aclaracion": not criterios_editados.producto}
        )
    prioridad = prioridad_elegida or criterios.prioridad

    estado: Literal["resultados", "requiere_aclaracion", "sin_cobertura"]
    comparacion, ordenadas, otros = None, [], []
    if criterios.requiere_aclaracion:
        estado, con_cobertura = "requiere_aclaracion", None
    else:
        encontrados = buscar_productos(sesion, criterios, configuracion.busqueda_puntaje_minimo)
        if not encontrados:
            estado, con_cobertura = "sin_cobertura", False
        else:
            estado, con_cobertura = "resultados", True
            principal = encontrados[0].producto
            comparacion, ordenadas = comparar_producto(
                sesion, principal, prioridad, criterios.precio_max_cop, configuracion
            )
            otros = [ProductoResumen(id=e.producto.id, nombre=e.producto.nombre_canonico) for e in encontrados[1:]]

    consulta = Consulta(
        texto_original=texto_limpio,
        criterios=criterios.model_dump(),
        confianza=criterios.confianza,
        tiempo_respuesta_ms=round((time.perf_counter() - inicio) * 1000),
        tokens_consumidos=tokens,
        con_cobertura=con_cobertura,
    )
    sesion.add(consulta)
    for posicion, calculada in enumerate(ordenadas, start=1):
        sesion.add(
            Recomendacion(
                consulta=consulta,
                oferta_id=calculada.oferta.oferta_id,
                posicion=posicion,
                costo_total_cop=calculada.costo_total,
                componentes={
                    "precio_cop": calculada.oferta.precio_cop,
                    "envio_cop": calculada.oferta.envio_cop,
                    "dias_entrega": calculada.oferta.dias_entrega,
                    "w": comparacion.w,
                    "costo_ajustado_cop": calculada.costo_ajustado,
                    "capturado_en": calculada.oferta.capturado_en.isoformat(),
                },
            )
        )
    sesion.commit()

    return RespuestaConsulta(
        consulta_id=consulta.id,
        estado=estado,
        criterios=criterios,
        comparacion=comparacion,
        otros_productos=otros,
    )
