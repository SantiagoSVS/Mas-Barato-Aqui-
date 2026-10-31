"""Punto de entrada de la API de Mas Barato Aquí!"""

from fastapi import FastAPI

from app.rutas import salud

app = FastAPI(
    title="Mas Barato Aquí! API",
    description="Compara el costo total estimado (precio + envío) entre tiendas que venden en Colombia.",
    version="0.1.0",
)

app.include_router(salud.router)
