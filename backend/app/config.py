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

    # Mercado Libre (API oficial). Sin credenciales, el conector no se activa.
    mercadolibre_client_id: str | None = None
    mercadolibre_client_secret: str | None = None
    # Ciudad a la que se cotiza el envío (id de /classified_locations). Por defecto, Medellín.
    mercadolibre_ciudad_destino: str = "TUNPQ01FRGRjNjc4"
    mercadolibre_productos_por_termino: int = 5
    mercadolibre_ofertas_por_producto: int = 5


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
