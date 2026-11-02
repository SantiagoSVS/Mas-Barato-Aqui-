"""Búsqueda sobre los datos ya capturados (nunca se consulta una tienda en este momento).

1. Productos del catálogo que corresponden a los criterios: la marca debe coincidir si el
   usuario la dio, y el texto (producto, modelo y atributos) se compara con el nombre del
   producto usando similitud de palabras (RapidFuzz, token_set_ratio).
2. Ofertas vigentes de un producto: la última captura de cada oferta, solo de tiendas activas.
"""

import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.costo.motor import OfertaVigente
from app.interpretacion.esquema import CriteriosConsulta
from app.modelos import Captura, Oferta, Plataforma, Producto


@dataclass(frozen=True)
class ProductoEncontrado:
    producto: Producto
    puntaje: float


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def texto_de_busqueda(criterios: CriteriosConsulta) -> str:
    partes = [criterios.producto, criterios.modelo, *criterios.atributos.values()]
    return _normalizar(" ".join(p for p in partes if p))


def buscar_productos(sesion: Session, criterios: CriteriosConsulta, puntaje_minimo: int) -> list[ProductoEncontrado]:
    """Productos que corresponden a los criterios, del más parecido al menos parecido."""
    if not criterios.producto:
        return []
    consulta = texto_de_busqueda(criterios)
    encontrados = []
    for producto in sesion.scalars(select(Producto)):
        if criterios.marca and producto.marca and _normalizar(criterios.marca) != _normalizar(producto.marca):
            continue
        texto_producto = _normalizar(" ".join(p for p in (producto.nombre_canonico, producto.modelo) if p))
        puntaje = fuzz.token_set_ratio(consulta, texto_producto)
        if puntaje >= puntaje_minimo:
            encontrados.append(ProductoEncontrado(producto, puntaje))
    return sorted(encontrados, key=lambda e: (-e.puntaje, e.producto.nombre_canonico))


def ofertas_vigentes(sesion: Session, producto_id: int) -> list[OfertaVigente]:
    """Última captura de cada oferta del producto, en tiendas activas."""
    filas = sesion.execute(
        select(Oferta, Plataforma.nombre, Captura)
        .join(Plataforma, Plataforma.id == Oferta.plataforma_id)
        .join(Captura, Captura.oferta_id == Oferta.id)
        .where(Oferta.producto_id == producto_id, Plataforma.activa)
        .ext(distinct_on(Oferta.id))
        .order_by(Oferta.id, Captura.capturado_en.desc())
    ).all()
    return [
        OfertaVigente(
            oferta_id=oferta.id,
            plataforma=plataforma,
            titulo=oferta.titulo_original,
            url=oferta.url_origen,
            vendedor=oferta.vendedor,
            precio_cop=captura.precio_cop,
            envio_cop=captura.envio_cop,
            dias_entrega=captura.dias_entrega,
            disponible=captura.disponible,
            capturado_en=captura.capturado_en,
        )
        for oferta, plataforma, captura in filas
    ]


def plataformas_activas(sesion: Session) -> list[Plataforma]:
    return list(sesion.scalars(select(Plataforma).where(Plataforma.activa).order_by(Plataforma.nombre)))
