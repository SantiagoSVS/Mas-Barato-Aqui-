"""Muestra cómo interpreta el sistema una consulta (útil para demostraciones y pruebas).

    python -m app.herramientas.interpretar "busco un celular Samsung gama media por menos de 800 mil"
"""

import argparse
import json
import sys

from app.config import obtener_configuracion
from app.interpretacion.interprete import ErrorConsulta
from app.interpretacion.registro import crear_interprete


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("consulta", help="la consulta, entre comillas")
    argumentos = parser.parse_args()

    try:
        resultado = crear_interprete(obtener_configuracion()).interpretar(argumentos.consulta)
    except ErrorConsulta as error:
        print(f"Consulta no válida: {error}", file=sys.stderr)
        return 1

    print(json.dumps(resultado.criterios.model_dump(), ensure_ascii=False, indent=2))
    print(
        f"\nProveedor: {resultado.proveedor} · intentos: {resultado.intentos} · "
        f"respuesta válida: {'sí' if resultado.respuesta_valida else 'no'} · "
        f"tokens: {resultado.tokens_entrada} de entrada, {resultado.tokens_salida} de salida"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
