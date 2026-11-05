"""Límites de consultas (sección 9: controlan el consumo de tokens sin cuentas de usuario).

1. Por dirección IP: ventana deslizante en memoria, hasta N consultas por minuto. Basta para un
   solo proceso de la API; si se despliegan varios, habría que compartir los contadores.
2. Cupo total del modelo: llamadas en las últimas 24 horas, contadas en la base de datos. Sobrevive
   a los reinicios del servicio y no depende de la IP, que un cliente puede falsear tras un proxy.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos import Consulta


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


def cupo_del_modelo_agotado(sesion: Session, maximo: int | None) -> bool:
    """Dice si ya se hicieron `maximo` llamadas al modelo en 24 horas (None: sin tope)."""
    if maximo is None:
        return False
    desde = datetime.now(UTC) - timedelta(hours=24)
    llamadas = sesion.scalar(
        select(func.count()).select_from(Consulta).where(Consulta.creada_en >= desde, Consulta.tokens_consumidos > 0)
    )
    return llamadas >= maximo
