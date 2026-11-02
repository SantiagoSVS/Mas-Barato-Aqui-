"""Registra Homecenter como plataforma (extracción de su página, precios en pesos).

Reemplaza a Amazon como tercera tienda del MVP (el documento exige al menos tres).
Queda INACTIVA hasta revisar los términos de Homecenter, como exige el documento de
arquitectura; después se activa con una migración, igual que Falabella.

Revision ID: 44e5130a1c77
Revises: 79656182dbed
Create Date: 2026-11-01 19:25:41.084851

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '44e5130a1c77'
down_revision: Union[str, Sequence[str], None] = '79656182dbed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la plataforma, salvo que ya exista con ese nombre."""
    op.execute(
        "INSERT INTO plataforma (nombre, tipo_acceso, url_base, moneda, activa) "
        "VALUES ('Homecenter', 'extraccion', 'https://www.homecenter.com.co', 'COP', false) "
        "ON CONFLICT (nombre) DO NOTHING"
    )


def downgrade() -> None:
    """Quita la plataforma solo si no tiene ofertas ni ejecuciones asociadas."""
    op.execute(
        "DELETE FROM plataforma WHERE nombre = 'Homecenter' "
        "AND NOT EXISTS (SELECT 1 FROM oferta WHERE oferta.plataforma_id = plataforma.id) "
        "AND NOT EXISTS (SELECT 1 FROM ejecucion_captura e WHERE e.plataforma_id = plataforma.id)"
    )
