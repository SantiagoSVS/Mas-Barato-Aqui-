"""Entorno de Alembic: conecta las migraciones con los modelos y con DATABASE_URL."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app import modelos  # noqa: F401  (registra las tablas en Base.metadata)
from app.config import obtener_configuracion
from app.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Orden de prioridad de la URL: la que pasan las pruebas en config.attributes, la de la línea
# de comandos (alembic -x url_bd=...) y, si no hay ninguna, DATABASE_URL de .env
url_bd = (
    config.attributes.get("url_bd")
    or context.get_x_argument(as_dictionary=True).get("url_bd")
    or obtener_configuracion().database_url
)


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse (alembic upgrade head --sql)."""
    context.configure(
        url=url_bd,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones sobre la base de datos."""
    motor = create_engine(url_bd, connect_args={"connect_timeout": 5})
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    motor.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
