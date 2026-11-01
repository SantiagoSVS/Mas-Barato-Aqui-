"""Cliente HTTP para extraer datos de forma respetuosa (sección 5.1 y marco legal).

- Se identifica con un User-Agent propio.
- Respeta robots.txt (RFC 9309) en las páginas web.
- Espera un intervalo mínimo entre peticiones al mismo dominio.
- No envía credenciales ni cookies de sesión: nunca accede a contenido detrás de autenticación.

Las APIs oficiales no se rigen por robots.txt sino por sus propios términos, por eso esas
peticiones se marcan con es_api_oficial=True.
"""

import time
from collections.abc import Callable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

from app.extraccion.conector import ErrorConector


class AccesoNoPermitido(ErrorConector):
    """robots.txt no permite consultar esa URL."""


class ErrorHttp(ErrorConector):
    """El servidor respondió con un código de error (4xx o 5xx)."""

    def __init__(self, url: str, status_code: int) -> None:
        super().__init__(f"{url} respondió {status_code}")
        self.status_code = status_code


class ClienteHttp:
    def __init__(
        self,
        user_agent: str,
        intervalo_minimo_s: float,
        timeout_s: float,
        sesion: requests.Session | None = None,
        reloj: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self.user_agent = user_agent
        self.intervalo_minimo_s = intervalo_minimo_s
        self.timeout_s = timeout_s
        self._sesion = sesion or requests.Session()
        self._reloj = reloj
        self._dormir = dormir
        self._ultima_peticion: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser] = {}

    def get(
        self,
        url: str,
        params: dict[str, str] | None = None,
        encabezados: dict[str, str] | None = None,
        es_api_oficial: bool = False,
    ) -> requests.Response:
        if not es_api_oficial and not self._permitido_por_robots(url):
            raise AccesoNoPermitido(f"robots.txt no permite consultar {url}")

        respuesta = self._pedir(url, params, encabezados)
        if respuesta.status_code >= 400:
            raise ErrorHttp(url, respuesta.status_code)
        return respuesta

    def post_api(
        self, url: str, datos: dict[str, str], encabezados: dict[str, str] | None = None
    ) -> requests.Response:
        """POST solo para APIs oficiales (por ejemplo, pedir un token de acceso)."""
        self._esperar_turno(urlsplit(url).netloc)
        try:
            respuesta = self._sesion.post(
                url,
                data=datos,
                headers={**(encabezados or {}), "User-Agent": self.user_agent},
                timeout=self.timeout_s,
            )
        except requests.RequestException as error:
            raise ErrorConector(f"No se pudo consultar {url}: {error}") from error
        if respuesta.status_code >= 400:
            raise ErrorHttp(url, respuesta.status_code)
        return respuesta

    def _pedir(
        self,
        url: str,
        params: dict[str, str] | None = None,
        encabezados: dict[str, str] | None = None,
    ) -> requests.Response:
        self._esperar_turno(urlsplit(url).netloc)
        try:
            return self._sesion.get(
                url,
                params=params,
                headers={**(encabezados or {}), "User-Agent": self.user_agent},
                timeout=self.timeout_s,
                allow_redirects=True,
            )
        except requests.RequestException as error:
            raise ErrorConector(f"No se pudo consultar {url}: {error}") from error

    def _esperar_turno(self, dominio: str) -> None:
        """Límite de frecuencia: deja pasar al menos intervalo_minimo_s entre peticiones."""
        ultima = self._ultima_peticion.get(dominio)
        if ultima is not None:
            faltante = self.intervalo_minimo_s - (self._reloj() - ultima)
            if faltante > 0:
                self._dormir(faltante)
        self._ultima_peticion[dominio] = self._reloj()

    def _permitido_por_robots(self, url: str) -> bool:
        partes = urlsplit(url)
        dominio = partes.netloc
        if dominio not in self._robots:
            self._robots[dominio] = self._leer_robots(f"{partes.scheme}://{dominio}/robots.txt")
        return self._robots[dominio].can_fetch(self.user_agent, url)

    def _leer_robots(self, url_robots: str) -> RobotFileParser:
        """Lee robots.txt siguiendo la RFC 9309, sección 2.3.1:

        - 2xx: se aplican sus reglas.
        - 4xx: no hay restricciones (el archivo no existe).
        - 5xx o sin respuesta: se asume que todo está prohibido.
        """
        robots = RobotFileParser(url_robots)
        try:
            respuesta = self._pedir(url_robots)
        except ErrorConector:
            robots.disallow_all = True
            return robots

        if 200 <= respuesta.status_code < 300:
            robots.parse(respuesta.text.splitlines())
        elif 400 <= respuesta.status_code < 500:
            robots.allow_all = True
        else:
            robots.disallow_all = True
        return robots
