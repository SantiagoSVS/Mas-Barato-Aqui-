"""Sitio de producción: la API en /api y la interfaz compilada en todo lo demás.

En desarrollo, Vite hace esta misma unión con su proxy. Aquí la API va bajo /api porque
comparte rutas con la interfaz: /productos/5/historial es una pantalla para el navegador.

    uvicorn --factory app.produccion:crear_sitio
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from starlette.exceptions import HTTPException as HTTPExceptionStarlette
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.config import RAIZ_PROYECTO
from app.main import app as api

CARPETA_INTERFAZ = RAIZ_PROYECTO / "frontend" / "dist"


class InterfazEstatica(StaticFiles):
    """Archivos de la interfaz. Las rutas de pantallas (/resultados) las resuelve React en index.html."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except (HTTPException, HTTPExceptionStarlette) as error:
            es_archivo = "." in path.rsplit("/", 1)[-1]  # /assets/x.js que no existe sigue siendo 404
            if error.status_code != 404 or es_archivo:
                raise
            return await super().get_response("index.html", scope)


def crear_sitio(carpeta: Path = CARPETA_INTERFAZ) -> FastAPI:
    sitio = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    sitio.mount("/api", api)
    sitio.mount("/", InterfazEstatica(directory=carpeta, html=True))
    return sitio
