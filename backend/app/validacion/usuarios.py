"""Análisis de las pruebas con usuarios: H1 (tiempo de decisión) y H5 (costo de la opción elegida).

Diseño intra-sujeto: cada participante resuelve cada tarea con la app y de forma manual, en orden
alterno entre participantes. Un "par" es la misma tarea del mismo participante en las dos
condiciones; las comparaciones se hacen sobre pares.

Reglas (decididas antes de recoger datos, para no ajustarlas a los resultados):
- Un par entra al análisis de H1 solo si la tarea se completó en las dos condiciones.
- Un par entra al análisis de H5 si además se conoce el costo total en las dos condiciones
  (precio + envío visibles antes de pagar). Si el envío no era visible, el costo queda
  incompleto y el par se reporta aparte, sin adivinar el envío.
- H1 se cumple si la mediana de la reducción de tiempo por par es de al menos 50 % y la
  diferencia es significativa (p < 0,05).
- H5 se cumple si en al menos el 80 % de los pares el costo con la app es menor o igual al manual.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from app.validacion.estadistica import Comparacion, comparar_pareadas, intervalo_wilson, resumen

META_H1 = 0.50  # reducción mínima del tiempo de decisión
META_H5 = 0.80  # proporción mínima de tareas con costo app <= manual
CONDICIONES = ("app", "manual")
COLUMNAS = ("participante", "tarea", "categoria", "condicion", "orden", "tiempo_s", "completada",
            "tienda", "precio_cop", "envio_cop", "observaciones")


@dataclass(frozen=True)
class Registro:
    participante: str
    tarea: str
    categoria: str
    condicion: str
    tiempo_s: float
    completada: bool
    tienda: str
    precio_cop: int | None
    envio_cop: int | None  # None: el envío no era visible antes de pagar

    @property
    def costo_total_cop(self) -> int | None:
        if self.precio_cop is None or self.envio_cop is None:
            return None
        return self.precio_cop + self.envio_cop


@dataclass(frozen=True)
class Par:
    participante: str
    tarea: str
    categoria: str
    app: Registro
    manual: Registro

    @property
    def completado(self) -> bool:
        return self.app.completada and self.manual.completada

    @property
    def con_costos(self) -> bool:
        return self.completado and self.app.costo_total_cop is not None and self.manual.costo_total_cop is not None

    @property
    def reduccion_tiempo(self) -> float:
        """Fracción del tiempo manual que se ahorra con la app (0,6 = 60 % menos)."""
        return 1 - self.app.tiempo_s / self.manual.tiempo_s


def _entero(valor: str, campo: str, linea: int) -> int | None:
    valor = valor.strip().replace(".", "").replace("$", "")
    if not valor:
        return None
    try:
        return int(valor)
    except ValueError:
        raise ValueError(f"Línea {linea}: '{campo}' debe ser un número entero de pesos") from None


def leer_registro(ruta: Path) -> list[Registro]:
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        faltantes = set(COLUMNAS) - set(lector.fieldnames or [])
        if faltantes:
            raise ValueError(f"Faltan columnas en {ruta.name}: {', '.join(sorted(faltantes))}")
        registros = []
        for linea, fila in enumerate(lector, start=2):
            condicion = fila["condicion"].strip().lower()
            if condicion not in CONDICIONES:
                raise ValueError(f"Línea {linea}: la condición debe ser 'app' o 'manual'")
            completada = fila["completada"].strip().lower()
            if completada not in ("si", "sí", "no"):
                raise ValueError(f"Línea {linea}: 'completada' debe ser 'si' o 'no'")
            try:
                tiempo = float(fila["tiempo_s"].replace(",", "."))
            except ValueError:
                raise ValueError(f"Línea {linea}: 'tiempo_s' debe ser un número de segundos") from None
            if tiempo <= 0:
                raise ValueError(f"Línea {linea}: 'tiempo_s' debe ser mayor que cero")
            registros.append(Registro(
                participante=fila["participante"].strip(),
                tarea=fila["tarea"].strip(),
                categoria=fila["categoria"].strip(),
                condicion=condicion,
                tiempo_s=tiempo,
                completada=completada != "no",
                tienda=fila["tienda"].strip(),
                precio_cop=_entero(fila["precio_cop"], "precio_cop", linea),
                envio_cop=_entero(fila["envio_cop"], "envio_cop", linea),
            ))
    return registros


def emparejar(registros: list[Registro]) -> tuple[list[Par], list[str]]:
    """Une la condición app y la manual de cada participante y tarea.

    Devuelve los pares y los avisos de registros sin pareja (se excluyen del análisis).
    """
    por_clave: dict[tuple[str, str], dict[str, Registro]] = {}
    for r in registros:
        condiciones = por_clave.setdefault((r.participante, r.tarea), {})
        if r.condicion in condiciones:
            raise ValueError(f"{r.participante} tiene dos registros de {r.tarea} con la condición '{r.condicion}'")
        condiciones[r.condicion] = r

    pares, avisos = [], []
    for (participante, tarea), condiciones in sorted(por_clave.items()):
        if len(condiciones) < 2:
            falta = "manual" if "app" in condiciones else "app"
            avisos.append(f"{participante} · {tarea}: falta la condición '{falta}'; se excluye")
            continue
        app, manual = condiciones["app"], condiciones["manual"]
        pares.append(Par(participante, tarea, app.categoria, app, manual))
    return pares, avisos


@dataclass(frozen=True)
class ResultadoH1:
    pares: int
    tiempos_app: dict[str, float]
    tiempos_manual: dict[str, float]
    mediana_reduccion: float
    comparacion: Comparacion

    @property
    def cumple(self) -> bool:
        return self.mediana_reduccion >= META_H1 and self.comparacion.significativa


def analizar_h1(pares: list[Par]) -> ResultadoH1:
    validos = [p for p in pares if p.completado]
    app = [p.app.tiempo_s for p in validos]
    manual = [p.manual.tiempo_s for p in validos]
    return ResultadoH1(
        pares=len(validos),
        tiempos_app=resumen(app),
        tiempos_manual=resumen(manual),
        mediana_reduccion=median(p.reduccion_tiempo for p in validos),
        comparacion=comparar_pareadas(app, manual),
    )


@dataclass(frozen=True)
class ResultadoH5:
    pares: int
    pares_sin_costo: int
    app_menor_o_igual: int
    intervalo: tuple[float, float]
    comparacion: Comparacion | None  # None si no se puede comparar (pocos pares o sin diferencias)

    @property
    def proporcion(self) -> float:
        return self.app_menor_o_igual / self.pares if self.pares else 0.0

    @property
    def cumple(self) -> bool:
        return self.proporcion >= META_H5


def analizar_h5(pares: list[Par]) -> ResultadoH5:
    completados = [p for p in pares if p.completado]
    validos = [p for p in completados if p.con_costos]
    favorables = sum(1 for p in validos if p.app.costo_total_cop <= p.manual.costo_total_cop)
    try:
        comparacion = comparar_pareadas([p.app.costo_total_cop for p in validos],
                                        [p.manual.costo_total_cop for p in validos])
    except ValueError:
        comparacion = None
    return ResultadoH5(
        pares=len(validos),
        pares_sin_costo=len(completados) - len(validos),
        app_menor_o_igual=favorables,
        intervalo=intervalo_wilson(favorables, len(validos)),
        comparacion=comparacion,
    )


def leer_sus(ruta: Path) -> dict[str, list[int]]:
    """Lee las respuestas SUS: columnas participante, p1 … p10."""
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        respuestas = {}
        for linea, fila in enumerate(lector, start=2):
            participante = fila["participante"].strip()
            if participante in respuestas:
                raise ValueError(f"Línea {linea}: {participante} aparece dos veces en el SUS")
            try:
                respuestas[participante] = [int(fila[f"p{i}"]) for i in range(1, 11)]
            except (KeyError, ValueError):
                raise ValueError(f"Línea {linea}: las respuestas p1 a p10 deben ser números de 1 a 5") from None
    return respuestas
