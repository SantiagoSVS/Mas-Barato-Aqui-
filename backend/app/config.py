"""Configuración del backend, leída de variables de entorno o del archivo .env de la raíz."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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
    # Segundos para conectar: 5 en local; más con una base en la nube que se suspende sin uso
    db_timeout_conexion_s: int = Field(default=5, ge=1)

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
    interprete_modelo: str = "claude-haiku-5-5"
    interprete_timeout_s: float = 30
    anthropic_api_key: str | None = Field(default=None, repr=False)
    # Por debajo de esta confianza se pide aclaración. Valor inicial: calibrar con las 50
    # consultas anotadas (H2).
    interprete_confianza_minima: float = 0.5

    # Costo total (sección 7). w = valor en pesos de cada día de espera para el perfil
    # "Entrega más rápida". NO está fijado: se calibra con las pruebas de usuarios. Mientras sea
    # None, ese perfil ordena igual que "Menor costo total" y la respuesta lo avisa.
    peso_dia_espera_cop: int | None = Field(default=None, ge=0)
    # Similitud mínima (0 a 100, RapidFuzz) entre la consulta y un producto del catálogo.
    # Valor inicial: ajustar con consultas reales.
    busqueda_puntaje_minimo: int = Field(default=80, ge=0, le=100)

    # Historial (RF-10): un precio está "cerca de su mínimo histórico" si no lo supera en más de
    # esta proporción (0.05 = 5 %). Valor inicial: el documento no lo fija; ajustar con usuarios.
    historial_umbral_cercania: float = Field(default=0.05, ge=0, le=1)

    # Seguridad (sección 9): consultas por minuto desde una misma IP. Valor inicial.
    limite_consultas_por_minuto: int = Field(default=20, ge=1)
    # Llamadas al modelo en 24 horas, en total; protege los créditos en un sitio público. Sin valor: sin tope
    limite_consultas_modelo_por_dia: int | None = Field(default=None, ge=1)

    @field_validator("database_url", "test_database_url")
    @classmethod
    def usar_psycopg(cls, url: str | None) -> str | None:
        """Neon y otros servicios entregan postgresql://; SQLAlchemy debe saber que el controlador es psycopg."""
        if url is None:
            return None
        for prefijo in ("postgresql://", "postgres://"):
            if url.startswith(prefijo):
                return "postgresql+psycopg://" + url.removeprefix(prefijo)
        return url


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
