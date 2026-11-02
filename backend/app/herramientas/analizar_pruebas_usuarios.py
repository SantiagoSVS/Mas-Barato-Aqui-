"""Resultados de las pruebas con usuarios frente a H1, H4 y H5.

    python -m app.herramientas.analizar_pruebas_usuarios
    python -m app.herramientas.analizar_pruebas_usuarios --registro mis_tareas.csv --sus mi_sus.csv

Lee la hoja de registro de tareas y las respuestas del SUS (plantillas en
backend/evaluacion/usuarios/). Las reglas de análisis están en app/validacion/usuarios.py.
"""

import argparse
from pathlib import Path
from statistics import mean, median, stdev

from app.config import RAIZ_PROYECTO
from app.validacion.estadistica import ALFA, Comparacion
from app.validacion.sus import META_H4, intervalo_media, puntaje_sus
from app.validacion.usuarios import META_H1, META_H5, analizar_h1, analizar_h5, emparejar, leer_registro, leer_sus

CARPETA = RAIZ_PROYECTO / "backend" / "evaluacion" / "usuarios"


def _si_no(cumple: bool) -> str:
    return "SÍ" if cumple else "NO"


def _comparacion(c: Comparacion) -> str:
    normalidad = f"Shapiro-Wilk p = {c.p_normalidad:.3f}" if c.p_normalidad is not None else ""
    return (f"{c.prueba} (n = {c.n}; {normalidad}): estadístico = {c.estadistico:.2f}, "
            f"p = {c.p_valor:.4f} ({'significativa' if c.significativa else 'no significativa'} con α = {ALFA}); "
            f"{c.nombre_efecto} = {c.efecto:.2f}")


def _segundos(r: dict[str, float]) -> str:
    return f"mediana {r['mediana']:.0f} s (RIC {r['q1']:.0f} – {r['q3']:.0f} s)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Análisis de las pruebas con usuarios (H1, H4, H5)")
    parser.add_argument("--registro", type=Path, default=CARPETA / "registro_tareas.csv")
    parser.add_argument("--sus", type=Path, default=CARPETA / "sus.csv")
    argumentos = parser.parse_args()

    pares, avisos = emparejar(leer_registro(argumentos.registro))
    participantes = {p.participante for p in pares}
    print(f"Participantes: {len(participantes)} · pares tarea-condición: {len(pares)}")
    for aviso in avisos:
        print(f"  Aviso: {aviso}")
    incompletos = sum(1 for p in pares if not p.completado)
    if incompletos:
        print(f"  Pares con alguna tarea sin completar (se excluyen): {incompletos}")

    print("\nH1 · Tiempo de decisión")
    h1 = analizar_h1(pares)
    print(f"  Con la app: {_segundos(h1.tiempos_app)}")
    print(f"  Manual:     {_segundos(h1.tiempos_manual)}")
    print(f"  Reducción por par (mediana): {h1.mediana_reduccion:.1%}")
    print(f"  {_comparacion(h1.comparacion)}")
    print(f"  Meta H1 (reducción ≥ {META_H1:.0%} y diferencia significativa): {_si_no(h1.cumple)}")

    print("\nH5 · Costo de la opción elegida")
    h5 = analizar_h5(pares)
    bajo, alto = h5.intervalo
    print(f"  Pares con costo total conocido en las dos condiciones: {h5.pares}"
          f" (sin envío visible, excluidos: {h5.pares_sin_costo})")
    print(f"  Costo con la app ≤ manual: {h5.app_menor_o_igual} de {h5.pares} "
          f"({h5.proporcion:.1%}; IC 95 % {bajo:.1%} – {alto:.1%})")
    if h5.comparacion:
        print(f"  {_comparacion(h5.comparacion)}")
    print(f"  Meta H5 (≥ {META_H5:.0%} de las tareas): {_si_no(h5.cumple)}")

    print("\nH4 · Usabilidad (SUS)")
    puntajes = {p: puntaje_sus(r) for p, r in leer_sus(argumentos.sus).items()}
    valores = list(puntajes.values())
    bajo, alto = intervalo_media(valores)
    print(f"  Cuestionarios: {len(valores)}")
    print(f"  Media {mean(valores):.1f} (DE {stdev(valores):.1f}; IC 95 % {bajo:.1f} – {alto:.1f}) · "
          f"mediana {median(valores):.1f}")
    print(f"  Meta H4 (media ≥ {META_H4:.0f}): {_si_no(mean(valores) >= META_H4)}")


if __name__ == "__main__":
    main()
