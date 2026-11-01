"""Registra Mercado Libre como plataforma (API oficial, precios en pesos).

Revision ID: cd893242420a
Revises: 3d40e043026f
Create Date: 2026-11-01 12:00:07.025302

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'cd893242420a'
down_revision: Union[str, Sequence[str], None] = '3d40e043026f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la plataforma, salvo que ya exista con ese nombre."""
    op.execute(
        "INSERT INTO plataforma (nombre, tipo_acceso, url_base, moneda, activa) "
        "VALUES ('Mercado Libre', 'api', 'https://www.mercadolibre.com.co', 'COP', true) "
        "ON CONFLICT (nombre) DO NOTHING"
    )


def downgrade() -> None:
    """Quita la plataforma solo si no tiene ofertas ni ejecuciones asociadas."""
    op.execute(
        "DELETE FROM plataforma WHERE nombre = 'Mercado Libre' "
        "AND NOT EXISTS (SELECT 1 FROM oferta WHERE oferta.plataforma_id = plataforma.id) "
        "AND NOT EXISTS (SELECT 1 FROM ejecucion_captura e WHERE e.plataforma_id = plataforma.id)"
    )
