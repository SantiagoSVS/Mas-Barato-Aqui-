"""Elige el proveedor del modelo de lenguaje según la configuración (INTERPRETE_PROVEEDOR)."""

from collections.abc import Callable

from app.config import Configuracion
from app.interpretacion.interprete import Interprete
from app.interpretacion.proveedor import ProveedorModelo
from app.interpretacion.proveedor_anthropic import ProveedorAnthropic
from app.interpretacion.proveedor_falso import ProveedorFalso


def _anthropic(configuracion: Configuracion) -> ProveedorModelo:
    if not configuracion.anthropic_api_key:
        raise ValueError("INTERPRETE_PROVEEDOR=anthropic necesita ANTHROPIC_API_KEY en .env")
    return ProveedorAnthropic(
        api_key=configuracion.anthropic_api_key,
        modelo=configuracion.interprete_modelo,
        timeout_s=configuracion.interprete_timeout_s,
    )


PROVEEDORES: dict[str, Callable[[Configuracion], ProveedorModelo]] = {
    ProveedorFalso.nombre: lambda _: ProveedorFalso(),
    ProveedorAnthropic.nombre: _anthropic,
}


def crear_interprete(configuracion: Configuracion) -> Interprete:
    nombre = configuracion.interprete_proveedor
    if nombre not in PROVEEDORES:
        disponibles = ", ".join(sorted(PROVEEDORES))
        raise ValueError(f"INTERPRETE_PROVEEDOR={nombre!r} no existe. Disponibles: {disponibles}")
    return Interprete(PROVEEDORES[nombre](configuracion), configuracion.interprete_confianza_minima)
