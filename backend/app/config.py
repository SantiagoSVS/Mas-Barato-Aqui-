"""Configuración del backend, leída de variables de entorno o del archivo .env de la raíz."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_PROYECTO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    test_database_url: str | None = None

    # Extracción (valores iniciales de operación; se ajustan según lo que acepte cada tienda)
    captura_intervalo_horas: float = 12
    extraccion_intervalo_minimo_s: float = 5
    extraccion_timeout_s: float = 20
    extraccion_user_agent: str = (
        "MasBaratoAquiBot/0.1 (proyecto de grado; +https://github.com/SantiagoSVS/Mas-Barato-Aqui-)"
    )
    catalogo_path: Path = RAIZ_PROYECTO / "backend" / "catalogo.toml"


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
