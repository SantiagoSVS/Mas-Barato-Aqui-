"""Arranque del worker de captura.

    python -m app.worker            # captura ahora y luego cada CAPTURA_INTERVALO_HORAS
    python -m app.worker --una-vez  # una sola pasada (útil para probar)
"""

import argparse
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import obtener_configuracion
from app.db import FabricaSesiones
from app.extraccion.catalogo import leer_terminos
from app.extraccion.cliente_http import ClienteHttp
from app.extraccion.registro import CONECTORES
from app.extraccion.tasa_cambio import ProveedorTRM
from app.worker.capturas import ejecutar_capturas

log = logging.getLogger("app.worker")


def pasada_de_captura() -> None:
    configuracion = obtener_configuracion()
    cliente = ClienteHttp(
        user_agent=configuracion.extraccion_user_agent,
        intervalo_minimo_s=configuracion.extraccion_intervalo_minimo_s,
        timeout_s=configuracion.extraccion_timeout_s,
    )
    conectores = {nombre: fabrica(cliente) for nombre, fabrica in CONECTORES.items()}
    terminos = leer_terminos(configuracion.catalogo_path)

    log.info("Inicia captura: %d conectores, %d términos", len(conectores), len(terminos))
    with FabricaSesiones() as sesion:
        ejecutar_capturas(sesion, conectores, terminos, ProveedorTRM(cliente))
    log.info("Termina captura")


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker de captura de Mas Barato Aquí!")
    parser.add_argument("--una-vez", action="store_true", help="hace una sola pasada y termina")
    argumentos = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if argumentos.una_vez:
        pasada_de_captura()
        return

    horas = obtener_configuracion().captura_intervalo_horas
    programador = BlockingScheduler(timezone="America/Bogota")
    # La primera pasada corre ya (abajo); las siguientes, cada `horas`.
    # coalesce y max_instances=1: si una pasada se demora, no se acumulan ni se solapan.
    programador.add_job(
        pasada_de_captura,
        "interval",
        hours=horas,
        coalesce=True,
        max_instances=1,
        id="captura_periodica",
    )
    log.info("Worker iniciado: captura cada %s horas (Ctrl+C para detener)", horas)
    pasada_de_captura()
    try:
        programador.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Worker detenido")


if __name__ == "__main__":
    main()
