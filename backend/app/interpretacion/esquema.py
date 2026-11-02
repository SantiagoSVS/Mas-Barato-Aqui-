"""Esquema de salida del intérprete (sección 5.3 del documento de arquitectura).

Cualquier proveedor, real o falso, debe responder con un JSON que cumpla este esquema. La
respuesta se valida aquí antes de usarse: es un dato, nunca se ejecuta.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Perfiles de decisión (RF-11): w = 0 para costo_total; w > 0 para entrega_rapida
Prioridad = Literal["costo_total", "entrega_rapida"]


class CriteriosConsulta(BaseModel):
    """Criterios estructurados de una consulta de compra."""

    # extra="forbid": si el modelo agrega campos que no existen, la respuesta no es válida
    model_config = ConfigDict(extra="forbid")

    producto: str | None = Field(default=None, max_length=100)
    marca: str | None = Field(default=None, max_length=60)
    modelo: str | None = Field(default=None, max_length=80)
    atributos: dict[str, str] = Field(default_factory=dict, max_length=10)
    precio_max_cop: int | None = Field(default=None, gt=0, le=1_000_000_000)
    prioridad: Prioridad = "costo_total"
    confianza: float = Field(ge=0, le=1)
    requiere_aclaracion: bool


def criterios_sin_interpretar() -> CriteriosConsulta:
    """Respuesta cuando no se pudo interpretar la consulta: hay que pedir aclaración."""
    return CriteriosConsulta(confianza=0, requiere_aclaracion=True)
