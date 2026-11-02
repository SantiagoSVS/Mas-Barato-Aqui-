"""Elige el proveedor del modelo de lenguaje según la configuración (INTERPRETE_PROVEEDOR)."""

from app.config import Configuracion
from app.interpretacion.interprete import Interprete
from app.interpretacion.proveedor import ProveedorModelo
from app.interpretacion.proveedor_falso import ProveedorFalso

# PENDIENTE: agregar el proveedor real cuando se elija (costo por consulta, límites de uso,
# disponibilidad en Colombia). Su clave irá en .env, nunca en el código.
PROVEEDORES: dict[str, type[ProveedorModelo]] = {
    ProveedorFalso.nombre: ProveedorFalso,
}


def crear_interprete(configuracion: Configuracion) -> Interprete:
    nombre = configuracion.interprete_proveedor
    if nombre not in PROVEEDORES:
        disponibles = ", ".join(sorted(PROVEEDORES))
        raise ValueError(f"INTERPRETE_PROVEEDOR={nombre!r} no existe. Disponibles: {disponibles}")
    return Interprete(PROVEEDORES[nombre](), configuracion.interprete_confianza_minima)
