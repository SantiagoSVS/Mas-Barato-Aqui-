"""Conexión a PostgreSQL y sesión por petición."""

from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import obtener_configuracion

# Nombres predecibles para índices y restricciones, para que las migraciones sean estables
CONVENCION_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


# connect_timeout: si PostgreSQL no está encendido, falla en segundos en vez de quedarse colgado
motor = create_engine(
    obtener_configuracion().database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5}
)
FabricaSesiones = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


def obtener_sesion() -> Iterator[Session]:
    """Dependencia de FastAPI: abre una sesión por petición y la cierra al terminar."""
    with FabricaSesiones() as sesion:
        yield sesion
