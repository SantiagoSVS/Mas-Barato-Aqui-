"""Mide la exactitud del intérprete con consultas anotadas a mano (hipótesis H2).

    python -m app.herramientas.evaluar_interprete
    python -m app.herramientas.evaluar_interprete --archivo evaluacion/consultas_ejemplo.json --detalle
    python -m app.herramientas.evaluar_interprete --csv resultados_h2.csv

Usa el proveedor configurado en INTERPRETE_PROVEEDOR. Las reglas de comparación están en
app/interpretacion/evaluacion.py.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from app.config import RAIZ_PROYECTO, obtener_configuracion
from app.interpretacion.esquema import CriteriosConsulta
from app.interpretacion.evaluacion import CAMPOS, Reporte, ResultadoConsulta, campos_distintos, intervalo_wilson
from app.interpretacion.registro import crear_interprete

ARCHIVO_POR_DEFECTO = RAIZ_PROYECTO / "backend" / "evaluacion" / "consultas_anotadas.json"
META_H2 = 0.80


def leer_anotaciones(ruta: Path) -> list[dict]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    consultas = datos["consultas"]
    ids = [c["id"] for c in consultas]
    if len(ids) != len(set(ids)):
        raise ValueError("Hay identificadores de consulta repetidos")
    for c in consultas:
        # Valida cada anotación con el mismo esquema; la confianza no se evalúa
        c["esperado"] = CriteriosConsulta.model_validate({"confianza": 1, **c["esperado"]})
    return consultas


def evaluar(consultas: list[dict]) -> Reporte:
    interprete = crear_interprete(obtener_configuracion())
    reporte = Reporte()
    for c in consultas:
        obtenido = interprete.interpretar(c["consulta"]).criterios
        reporte.resultados.append(
            ResultadoConsulta(
                id=c["id"],
                consulta=c["consulta"],
                campos_distintos=campos_distintos(obtenido, c["esperado"]),
                obtenido=obtenido,
                esperado=c["esperado"],
            )
        )
    return reporte


def imprimir(reporte: Reporte, detalle: bool) -> None:
    bajo, alto = intervalo_wilson(reporte.correctas, reporte.total)
    print(f"Proveedor: {obtener_configuracion().interprete_proveedor}")
    print(f"Consultas: {reporte.total}")
    print(f"Correctas en todos los campos: {reporte.correctas} ({reporte.exactitud:.1%})")
    print(f"Intervalo de confianza 95 %: {bajo:.1%} – {alto:.1%}")
    cumple = "SÍ" if reporte.exactitud >= META_H2 else "NO"
    print(f"Meta H2 (≥ {META_H2:.0%}): {cumple}")
    if reporte.total < 50:
        print(f"Aviso: H2 exige al menos 50 consultas; este archivo tiene {reporte.total}.")

    print("\nAciertos por campo:")
    for campo, aciertos in reporte.aciertos_por_campo().items():
        print(f"  {campo:<20} {aciertos}/{reporte.total}")

    fallidas = [r for r in reporte.resultados if not r.correcta]
    if detalle and fallidas:
        print("\nConsultas con diferencias:")
        for r in fallidas:
            print(f"\n  [{r.id}] {r.consulta}")
            for campo in r.campos_distintos:
                print(f"    {campo}: esperado={getattr(r.esperado, campo)!r} obtenido={getattr(r.obtenido, campo)!r}")


def guardar_csv(reporte: Reporte, ruta: Path) -> None:
    with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:  # utf-8-sig: Excel lo abre bien
        escritor = csv.writer(archivo, delimiter=";")
        escritor.writerow(["id", "consulta", "correcta", "campos_distintos", *[f"obtenido_{c}" for c in CAMPOS]])
        for r in reporte.resultados:
            escritor.writerow(
                [r.id, r.consulta, "sí" if r.correcta else "no", ", ".join(r.campos_distintos)]
                + [json.dumps(getattr(r.obtenido, c), ensure_ascii=False) for c in CAMPOS]
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--archivo", type=Path, default=ARCHIVO_POR_DEFECTO, help="JSON con las consultas anotadas")
    parser.add_argument("--detalle", action="store_true", help="muestra las diferencias de cada consulta fallida")
    parser.add_argument("--csv", type=Path, help="guarda el resultado de cada consulta en un CSV")
    argumentos = parser.parse_args()

    if not argumentos.archivo.exists():
        print(f"No existe {argumentos.archivo}.", file=sys.stderr)
        print("Crea el archivo con el formato de evaluacion/consultas_ejemplo.json.", file=sys.stderr)
        return 1

    reporte = evaluar(leer_anotaciones(argumentos.archivo))
    imprimir(reporte, argumentos.detalle)
    if argumentos.csv:
        guardar_csv(reporte, argumentos.csv)
        print(f"\nResultados guardados en {argumentos.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
