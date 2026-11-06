"""Búsqueda sobre los datos ya capturados (nunca se consulta una tienda en este momento).

1. Productos del catálogo que corresponden a los criterios. El texto (producto, modelo y
   atributos con números, como "55 pulgadas") se compara con el nombre del producto usando
   similitud de palabras (RapidFuzz, token_set_ratio). Los atributos descriptivos ("económica",
   "estudio") solo ayudan a ordenar: casi nunca están en el nombre y no deben descartar nada.
   La marca debe coincidir si el usuario la dio, salvo que el modelo identifique el producto:
   en "tarjeta RTX 4060 NVIDIA" el producto registrado puede ser de marca Gigabyte.
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


PALABRAS_VACIAS = {"de", "del", "el", "la", "los", "las", "un", "una", "para", "con", "y"}


@dataclass(frozen=True)
class ProductoEncontrado:
    producto: Producto
    puntaje: float
    afinidad: float = 0  # parecido contando todos los atributos; solo sirve para ordenar


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def texto_de_busqueda(criterios: CriteriosConsulta) -> str:
    atributos = [v for v in criterios.atributos.values() if any(c.isdigit() for c in v)]
    return _sin_palabras_vacias(" ".join(p for p in (criterios.producto, criterios.modelo, *atributos) if p))


def _sin_palabras_vacias(texto: str) -> str:
    return " ".join(p for p in _normalizar(texto).split() if p not in PALABRAS_VACIAS)


def _marca_compatible(criterios: CriteriosConsulta, producto: Producto, texto_producto: str) -> bool:
    if not criterios.marca or not producto.marca or _normalizar(criterios.marca) == _normalizar(producto.marca):
        return True
    return bool(criterios.modelo) and set(_sin_palabras_vacias(criterios.modelo).split()) <= set(texto_producto.split())


def buscar_productos(sesion: Session, criterios: CriteriosConsulta, puntaje_minimo: int) -> list[ProductoEncontrado]:
    """Productos que corresponden a los criterios, del más parecido al menos parecido."""
    if not criterios.producto:
        return []
    consulta = texto_de_busqueda(criterios)
    encontrados = []
    todos_los_atributos = _sin_palabras_vacias(" ".join(criterios.atributos.values()))
    for producto in sesion.scalars(select(Producto)):
        texto_producto = _sin_palabras_vacias(" ".join(p for p in (producto.nombre_canonico, producto.modelo) if p))
        if not _marca_compatible(criterios, producto, texto_producto):
            continue
        # Sin marca registrada (consolas, juegos), la marca dicha cuenta como una palabra más: "Xbox"
        texto = f"{consulta} {_normalizar(criterios.marca)}" if criterios.marca and not producto.marca else consulta
        puntaje = fuzz.token_set_ratio(texto, texto_producto)
        if puntaje >= puntaje_minimo:
            afinidad = fuzz.token_set_ratio(f"{texto} {todos_los_atributos}", texto_producto)
            encontrados.append(ProductoEncontrado(producto, puntaje, afinidad))
    return sorted(encontrados, key=lambda e: (-e.puntaje, -e.afinidad, e.producto.nombre_canonico))


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
