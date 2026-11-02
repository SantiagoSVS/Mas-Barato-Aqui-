"""Activa Homecenter: Santiago revisó sus términos y condiciones el 1 de noviembre de 2026.

Revision ID: 4d4c10d25b7b
Revises: 44e5130a1c77
Create Date: 2026-11-01 19:34:03.045305

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4d4c10d25b7b'
down_revision: Union[str, Sequence[str], None] = '44e5130a1c77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Activa la plataforma."""
    op.execute("UPDATE plataforma SET activa = true WHERE nombre = 'Homecenter'")


def downgrade() -> None:
    """La deja inactiva otra vez."""
    op.execute("UPDATE plataforma SET activa = false WHERE nombre = 'Homecenter'")
