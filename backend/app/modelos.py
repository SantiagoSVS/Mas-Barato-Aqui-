"""Modelo de datos (sección 6 del documento de arquitectura).

Separa lo estable (plataforma, producto, oferta) de lo que cambia (cada captura de precio),
porque de esa separación sale el historial. Los valores en pesos se guardan como enteros (COP).
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

TIPOS_ACCESO = ("api", "extraccion")
ESTADOS_EJECUCION = ("en_curso", "exitosa", "parcial", "fallida")


class Plataforma(Base):
    """Tienda que se compara (Amazon, Mercado Libre, Falabella, ...)."""

    __tablename__ = "plataforma"
    __table_args__ = (
        CheckConstraint(f"tipo_acceso IN {TIPOS_ACCESO}", name="tipo_acceso_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    tipo_acceso: Mapped[str] = mapped_column(String(20))
    url_base: Mapped[str] = mapped_column(String(255))
    moneda: Mapped[str] = mapped_column(String(3))  # ISO 4217: COP, USD
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    ofertas: Mapped[list["Oferta"]] = relationship(back_populates="plataforma")
    ejecuciones: Mapped[list["EjecucionCaptura"]] = relationship(back_populates="plataforma")


class EjecucionCaptura(Base):
    """Registro de cada pasada del worker por una plataforma (sección 5.1, RNF-05, RF-12).

    Si la plataforma falla, el error queda aquí y el worker sigue con las demás.
    "parcial" significa que algunas búsquedas fallaron y otras no.
    """

    __tablename__ = "ejecucion_captura"
    __table_args__ = (
        Index("ix_ejecucion_captura_plataforma_id_iniciada_en", "plataforma_id", "iniciada_en"),
        CheckConstraint(f"estado IN {ESTADOS_EJECUCION}", name="estado_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plataforma_id: Mapped[int] = mapped_column(ForeignKey("plataforma.id"))
    iniciada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    terminada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(20))
    ofertas_capturadas: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    errores: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    mensaje_error: Mapped[str | None] = mapped_column(Text)

    plataforma: Mapped[Plataforma] = relationship(back_populates="ejecuciones")


class Producto(Base):
    """Producto canónico que agrupa las ofertas equivalentes de distintas tiendas."""

    __tablename__ = "producto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_canonico: Mapped[str] = mapped_column(String(255), unique=True)
    marca: Mapped[str | None] = mapped_column(String(80))
    modelo: Mapped[str | None] = mapped_column(String(120))
    categoria: Mapped[str] = mapped_column(String(80))
    atributos: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    ofertas: Mapped[list["Oferta"]] = relationship(back_populates="producto")


class Oferta(Base):
    """Publicación de un producto en una tienda.

    producto_id queda vacío mientras la oferta no se haya emparejado, o si el emparejamiento
    fue dudoso: ante la duda se omite la oferta en lugar de mezclarla (sección 5.2).
    """

    __tablename__ = "oferta"
    __table_args__ = (UniqueConstraint("plataforma_id", "url_origen"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plataforma_id: Mapped[int] = mapped_column(ForeignKey("plataforma.id"))
    producto_id: Mapped[int | None] = mapped_column(ForeignKey("producto.id"), index=True)
    titulo_original: Mapped[str] = mapped_column(Text)
    url_origen: Mapped[str] = mapped_column(Text)
    vendedor: Mapped[str | None] = mapped_column(String(255))

    plataforma: Mapped[Plataforma] = relationship(back_populates="ofertas")
    producto: Mapped[Producto | None] = relationship(back_populates="ofertas")
    capturas: Mapped[list["Captura"]] = relationship(back_populates="oferta")


class Captura(Base):
    """Un punto del historial de precios de una oferta. Nunca se sobrescribe.

    Para tiendas en dólares (Amazon) se guardan también el precio original y la tasa de cambio
    usada, para poder auditar la conversión. Envío o días desconocidos quedan vacíos.
    """

    __tablename__ = "captura"
    __table_args__ = (
        Index("ix_captura_oferta_id_capturado_en", "oferta_id", "capturado_en"),
        CheckConstraint("precio_cop >= 0", name="precio_no_negativo"),
        CheckConstraint("envio_cop IS NULL OR envio_cop >= 0", name="envio_no_negativo"),
        CheckConstraint("dias_entrega IS NULL OR dias_entrega >= 0", name="dias_no_negativos"),
        CheckConstraint(
            "(precio_original IS NULL AND moneda_original IS NULL AND tasa_cambio IS NULL)"
            " OR (precio_original IS NOT NULL AND moneda_original IS NOT NULL"
            " AND tasa_cambio IS NOT NULL)",
            name="conversion_completa",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    oferta_id: Mapped[int] = mapped_column(ForeignKey("oferta.id"))
    capturado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    precio_cop: Mapped[int] = mapped_column(BigInteger)
    envio_cop: Mapped[int | None] = mapped_column(BigInteger)
    dias_entrega: Mapped[int | None] = mapped_column(Integer)
    disponible: Mapped[bool] = mapped_column(Boolean)
    precio_original: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    moneda_original: Mapped[str | None] = mapped_column(String(3))
    tasa_cambio: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    oferta: Mapped[Oferta] = relationship(back_populates="capturas")


class Consulta(Base):
    """Consulta de un usuario, registrada para las métricas y pruebas de validación (RF-12)."""

    __tablename__ = "consulta"

    id: Mapped[int] = mapped_column(primary_key=True)
    texto_original: Mapped[str] = mapped_column(String(300))
    criterios: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confianza: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    tiempo_respuesta_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_consumidos: Mapped[int | None] = mapped_column(Integer)
    con_cobertura: Mapped[bool] = mapped_column(Boolean)

    recomendaciones: Mapped[list["Recomendacion"]] = relationship(back_populates="consulta")


class Recomendacion(Base):
    """Posición de una oferta en la respuesta a una consulta, con los componentes del cálculo."""

    __tablename__ = "recomendacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    consulta_id: Mapped[int] = mapped_column(ForeignKey("consulta.id"), index=True)
    oferta_id: Mapped[int] = mapped_column(ForeignKey("oferta.id"))
    posicion: Mapped[int] = mapped_column(Integer)
    costo_total_cop: Mapped[int] = mapped_column(BigInteger)
    componentes: Mapped[dict[str, Any]] = mapped_column(JSONB)

    consulta: Mapped[Consulta] = relationship(back_populates="recomendaciones")
    oferta: Mapped[Oferta] = relationship()
