"""Auditoría de precios (hipótesis H3). Dos pasos:

    python -m app.herramientas.auditoria_precios muestra                    # genera la planilla
    python -m app.herramientas.auditoria_precios muestra --tamano 100 --semilla 7
    python -m app.herramientas.auditoria_precios resultado evaluacion/auditoria_h3_ronda1.csv [otra.csv …]

`muestra` toma la última captura de cada oferta capturada en las últimas horas (24 por
defecto), así que conviene correrla justo después de una pasada del worker y verificar la
planilla ese mismo día. `resultado` acepta varias planillas (rondas en días distintos) y las
suma. Los criterios están en app/validacion/precios.py; el procedimiento, en
docs/fase4/auditoria_precios.md.
"""

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.config import RAIZ_PROYECTO
from app.db import FabricaSesiones
from app.modelos import Captura, Oferta, Plataforma, Producto
from app.validacion.precios import (
    META_H3,
    OfertaAuditable,
    Proporcion,
    analizar_h3,
    escribir_planilla,
    leer_planilla,
    muestra_estratificada,
)

CARPETA = RAIZ_PROYECTO / "backend" / "evaluacion"


def ofertas_recientes(horas: float) -> list[OfertaAuditable]:
    desde = datetime.now(UTC) - timedelta(hours=horas)
    ultima = (
        select(Captura.oferta_id, func.max(Captura.capturado_en).label("en"))
        .group_by(Captura.oferta_id)
        .subquery()
    )
    consulta = (
        select(Captura, Oferta, Plataforma.nombre, Producto)
        .join(ultima, (ultima.c.oferta_id == Captura.oferta_id) & (ultima.c.en == Captura.capturado_en))
        .join(Oferta, Oferta.id == Captura.oferta_id)
        .join(Plataforma, Plataforma.id == Oferta.plataforma_id)
        .join(Producto, Producto.id == Oferta.producto_id)
        .where(Plataforma.activa, Captura.capturado_en >= desde)
    )
    with FabricaSesiones() as sesion:
        return [
            OfertaAuditable(
                captura_id=captura.id,
                plataforma=plataforma,
                categoria=producto.categoria,
                producto=producto.nombre_canonico,
                url=oferta.url_origen,
                capturado_en=captura.capturado_en,
                precio_cop=captura.precio_cop,
                envio_cop=captura.envio_cop,
            )
            for captura, oferta, plataforma, producto in sesion.execute(consulta)
        ]


def generar_muestra(tamano: int, semilla: int, horas: float, salida: Path | None) -> None:
    ofertas = ofertas_recientes(horas)
    if not ofertas:
        sys.exit(f"No hay capturas de las últimas {horas:g} horas: corre primero el worker.")
    muestra = muestra_estratificada(ofertas, tamano, semilla)
    salida = salida or CARPETA / f"auditoria_h3_{datetime.now():%Y%m%d}.csv"
    escribir_planilla(salida, muestra)
    print(f"Planilla: {salida}")
    print(f"Ofertas en la muestra: {len(muestra)} de {len(ofertas)} capturadas en las últimas {horas:g} horas")
    if len(muestra) < tamano:
        print(f"Aviso: hay menos ofertas que el tamaño pedido ({tamano}). Completa la auditoría con "
              "otra ronda en otro día (o amplía el catálogo).")
    estratos: dict[tuple[str, str], int] = {}
    for o in muestra:
        estratos[(o.plataforma, o.categoria)] = estratos.get((o.plataforma, o.categoria), 0) + 1
    for (plataforma, categoria), n in sorted(estratos.items()):
        print(f"  {plataforma} · {categoria}: {n}")


def _linea(nombre: str, p: Proporcion) -> str:
    bajo, alto = p.intervalo
    return f"{nombre}: {p.aciertos} de {p.total} ({p.valor:.1%}; IC 95 % {bajo:.1%} – {alto:.1%})"


def mostrar_resultado(planillas: list[Path]) -> None:
    verificaciones = [v for ruta in planillas for v in leer_planilla(ruta)]
    r = analizar_h3(verificaciones)
    print(f"Ofertas verificadas: {r.verificadas} (no disponibles al verificar: {r.no_disponibles})")
    print(_linea("Precio correcto (H3)", r.precio))
    print(_linea("Envío correcto", r.envio))
    print(_linea("Precio y envío correctos", r.precio_y_envio))
    for plataforma, p in r.precio_por_plataforma.items():
        print("  " + _linea(plataforma, p))
    print(f"Meta H3 (≥ {META_H3:.0%} de precios correctos): {'SÍ' if r.cumple else 'NO'}")
    if r.verificadas < 100:
        print(f"Aviso: H3 pide al menos 100 verificaciones; van {r.verificadas}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoría de precios (H3)")
    pasos = parser.add_subparsers(dest="paso", required=True)
    m = pasos.add_parser("muestra", help="genera la planilla con la muestra estratificada")
    m.add_argument("--tamano", type=int, default=100)
    m.add_argument("--semilla", type=int, default=2026, help="para que la muestra sea reproducible")
    m.add_argument("--horas", type=float, default=24, help="antigüedad máxima de la captura")
    m.add_argument("--salida", type=Path)
    r = pasos.add_parser("resultado", help="calcula el porcentaje de acierto de una o más planillas")
    r.add_argument("planillas", type=Path, nargs="+")
    argumentos = parser.parse_args()

    if argumentos.paso == "muestra":
        generar_muestra(argumentos.tamano, argumentos.semilla, argumentos.horas, argumentos.salida)
    else:
        mostrar_resultado(argumentos.planillas)


if __name__ == "__main__":
    main()
