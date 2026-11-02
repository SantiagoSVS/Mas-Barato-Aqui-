"""Auditoría de precisión de los datos (hipótesis H3: al menos 95 % de precios correctos).

1. Se toma una muestra aleatoria de ofertas, estratificada por plataforma y categoría, con la
   última captura de cada una.
2. Una persona abre cada URL y anota el precio y el envío publicados (envío hacia Medellín,
   el mismo destino que usa la captura).
3. Se calcula el porcentaje de coincidencia con su intervalo de confianza.

Criterios:
- El precio es correcto si el publicado es exactamente el capturado (en pesos).
- El envío es correcto si coincide, o si la captura lo dejó desconocido y la página tampoco lo
  muestra antes de pagar.
- Las ofertas que ya no están disponibles al verificar se excluyen y se reportan aparte.
"""

import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.validacion.estadistica import intervalo_wilson

META_H3 = 0.95
COLUMNAS_CAPTURA = ("captura_id", "plataforma", "categoria", "producto", "url", "capturado_en",
                    "precio_capturado_cop", "envio_capturado_cop")
COLUMNAS_VERIFICACION = ("verificado_en", "disponible", "precio_publicado_cop", "envio_publicado_cop",
                         "observaciones")


@dataclass(frozen=True)
class OfertaAuditable:
    captura_id: int
    plataforma: str
    categoria: str
    producto: str
    url: str
    capturado_en: datetime
    precio_cop: int
    envio_cop: int | None


def muestra_estratificada(ofertas: list[OfertaAuditable], tamano: int, semilla: int) -> list[OfertaAuditable]:
    """Muestra aleatoria proporcional a cada estrato (plataforma, categoría), con al menos una
    oferta por estrato. Con la misma semilla se obtiene la misma muestra (reproducible).
    """
    if tamano >= len(ofertas):
        return sorted(ofertas, key=lambda o: o.captura_id)

    estratos: dict[tuple[str, str], list[OfertaAuditable]] = defaultdict(list)
    for o in sorted(ofertas, key=lambda o: o.captura_id):
        estratos[(o.plataforma, o.categoria)].append(o)
    if tamano < len(estratos):
        raise ValueError(f"La muestra ({tamano}) es menor que el número de estratos ({len(estratos)})")

    # Asignación proporcional con mínimo 1; lo que sobra va a los restos mayores
    cupos = {e: max(1, int(tamano * len(g) / len(ofertas))) for e, g in estratos.items()}
    restos = sorted(estratos, key=lambda e: (tamano * len(estratos[e]) / len(ofertas)) % 1, reverse=True)
    i = 0
    while sum(cupos.values()) < tamano:
        e = restos[i % len(restos)]
        if cupos[e] < len(estratos[e]):
            cupos[e] += 1
        i += 1
    while sum(cupos.values()) > tamano:  # solo pasa si el mínimo de 1 excedió el tamaño
        e = max(cupos, key=lambda e: cupos[e])
        cupos[e] -= 1

    azar = random.Random(semilla)
    muestra = []
    for e in sorted(estratos):
        muestra.extend(azar.sample(estratos[e], cupos[e]))
    return sorted(muestra, key=lambda o: o.captura_id)


def escribir_planilla(ruta: Path, muestra: list[OfertaAuditable]) -> None:
    """Planilla para la auditoría: los datos capturados y columnas vacías para lo verificado."""
    with ruta.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS_CAPTURA + COLUMNAS_VERIFICACION)
        for o in muestra:
            escritor.writerow([o.captura_id, o.plataforma, o.categoria, o.producto, o.url,
                               o.capturado_en.isoformat(timespec="minutes"), o.precio_cop,
                               "" if o.envio_cop is None else o.envio_cop, "", "", "", "", ""])


@dataclass(frozen=True)
class Verificacion:
    captura_id: int
    plataforma: str
    disponible: bool
    precio_correcto: bool
    envio_correcto: bool


def _entero(valor: str) -> int | None:
    valor = valor.strip().replace(".", "").replace("$", "")
    return int(valor) if valor else None


def leer_planilla(ruta: Path) -> list[Verificacion]:
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        verificaciones = []
        for linea, fila in enumerate(csv.DictReader(archivo), start=2):
            disponible = fila["disponible"].strip().lower()
            if disponible not in ("si", "sí", "no"):
                raise ValueError(f"Línea {linea}: falta verificar la oferta ('disponible' = si o no)")
            if disponible == "no":
                verificaciones.append(Verificacion(int(fila["captura_id"]), fila["plataforma"], False, False, False))
                continue
            try:
                publicado = _entero(fila["precio_publicado_cop"])
                envio_publicado = _entero(fila["envio_publicado_cop"])
                capturado = int(fila["precio_capturado_cop"])
                envio_capturado = _entero(fila["envio_capturado_cop"])
            except ValueError:
                raise ValueError(f"Línea {linea}: los precios deben ser números enteros de pesos") from None
            if publicado is None:
                raise ValueError(f"Línea {linea}: falta el precio publicado")
            verificaciones.append(Verificacion(
                captura_id=int(fila["captura_id"]),
                plataforma=fila["plataforma"],
                disponible=True,
                precio_correcto=publicado == capturado,
                envio_correcto=envio_publicado == envio_capturado,
            ))
    return verificaciones


@dataclass(frozen=True)
class Proporcion:
    aciertos: int
    total: int

    @property
    def valor(self) -> float:
        return self.aciertos / self.total if self.total else 0.0

    @property
    def intervalo(self) -> tuple[float, float]:
        return intervalo_wilson(self.aciertos, self.total)


@dataclass(frozen=True)
class ResultadoH3:
    verificadas: int
    no_disponibles: int
    precio: Proporcion
    envio: Proporcion
    precio_y_envio: Proporcion
    precio_por_plataforma: dict[str, Proporcion]

    @property
    def cumple(self) -> bool:
        return self.precio.valor >= META_H3


def analizar_h3(verificaciones: list[Verificacion]) -> ResultadoH3:
    disponibles = [v for v in verificaciones if v.disponible]
    n = len(disponibles)
    por_plataforma: dict[str, list[Verificacion]] = defaultdict(list)
    for v in disponibles:
        por_plataforma[v.plataforma].append(v)
    return ResultadoH3(
        verificadas=n,
        no_disponibles=len(verificaciones) - n,
        precio=Proporcion(sum(v.precio_correcto for v in disponibles), n),
        envio=Proporcion(sum(v.envio_correcto for v in disponibles), n),
        precio_y_envio=Proporcion(sum(v.precio_correcto and v.envio_correcto for v in disponibles), n),
        precio_por_plataforma={
            p: Proporcion(sum(v.precio_correcto for v in vs), len(vs)) for p, vs in sorted(por_plataforma.items())
        },
    )
