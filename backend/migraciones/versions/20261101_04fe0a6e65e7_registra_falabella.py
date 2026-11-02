"""Registra Falabella como plataforma (extracción de su página, precios en pesos).

Queda INACTIVA: el documento de arquitectura exige revisar los términos de cada tienda antes
de integrarla. Después de revisarlos, se activa con:

    UPDATE plataforma SET activa = true WHERE nombre = 'Falabella';

Revision ID: 04fe0a6e65e7
Revises: faa6744ca824
Create Date: 2026-11-01 12:43:15.419671

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '04fe0a6e65e7'
down_revision: Union[str, Sequence[str], None] = 'faa6744ca824'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la plataforma, salvo que ya exista con ese nombre."""
    op.execute(
        "INSERT INTO plataforma (nombre, tipo_acceso, url_base, moneda, activa) "
        "VALUES ('Falabella', 'extraccion', 'https://www.falabella.com.co', 'COP', false) "
        "ON CONFLICT (nombre) DO NOTHING"
    )


def downgrade() -> None:
    """Quita la plataforma solo si no tiene ofertas ni ejecuciones asociadas."""
    op.execute(
        "DELETE FROM plataforma WHERE nombre = 'Falabella' "
        "AND NOT EXISTS (SELECT 1 FROM oferta WHERE oferta.plataforma_id = plataforma.id) "
        "AND NOT EXISTS (SELECT 1 FROM ejecucion_captura e WHERE e.plataforma_id = plataforma.id)"
    )
