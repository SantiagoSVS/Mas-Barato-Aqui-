"""Límite de consultas por dirección IP (sección 9: controla el consumo de tokens sin cuentas).

Ventana deslizante en memoria: cada IP puede hacer hasta N consultas por minuto. Basta para
un solo proceso de la API; si se despliegan varios, habría que guardar los contadores en un
lugar compartido (por ejemplo, la base de datos).
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock


class LimitadorPorIp:
    def __init__(self, maximo: int, ventana_s: float = 60, reloj: Callable[[], float] = time.monotonic) -> None:
        self._maximo = maximo
        self._ventana_s = ventana_s
        self._reloj = reloj
        self._peticiones: dict[str, deque[float]] = defaultdict(deque)
        self._candado = Lock()

    def permitir(self, ip: str) -> bool:
        """Registra la petición y dice si está dentro del límite."""
        ahora = self._reloj()
        with self._candado:
            recientes = self._peticiones[ip]
            while recientes and ahora - recientes[0] >= self._ventana_s:
                recientes.popleft()
            if len(recientes) >= self._maximo:
                return False
            recientes.append(ahora)
            return True
