"""Configuración del backend, leída de variables de entorno o del archivo .env de la raíz."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_PROYECTO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # repr=False: los valores con claves nunca se imprimen (logs, errores de pytest, CI)
    database_url: str = Field(repr=False)
    test_database_url: str | None = Field(default=None, repr=False)

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
    mercadolibre_client_secret: str | None = Field(default=None, repr=False)
    # Ciudad a la que se cotiza el envío (id de /classified_locations). Por defecto, Medellín.
    mercadolibre_ciudad_destino: str = "TUNPQ01FRGRjNjc4"
    mercadolibre_ofertas_por_producto: int = 5

    # Interpretación de consultas. "falso" funciona con reglas, sin clave de API; "anthropic"
    # usa Claude (proveedor elegido el 1 nov 2026) y necesita ANTHROPIC_API_KEY.
    interprete_proveedor: str = "falso"
    interprete_modelo: str = "claude-opus-5-5"
    interprete_timeout_s: float = 30
    anthropic_api_key: str | None = Field(default=None, repr=False)
    # Por debajo de esta confianza se pide aclaración. Valor inicial: calibrar con las 50
    # consultas anotadas (H2).
    interprete_confianza_minima: float = 0.5


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
