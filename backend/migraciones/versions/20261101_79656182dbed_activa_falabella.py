"""Activa Falabella: Santiago revisó sus términos y condiciones el 1 de noviembre de 2026.

Revision ID: 79656182dbed
Revises: 04fe0a6e65e7
Create Date: 2026-11-01 12:56:31.325874

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '79656182dbed'
down_revision: Union[str, Sequence[str], None] = '04fe0a6e65e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Activa la plataforma."""
    op.execute("UPDATE plataforma SET activa = true WHERE nombre = 'Falabella'")


def downgrade() -> None:
    """La deja inactiva otra vez."""
    op.execute("UPDATE plataforma SET activa = false WHERE nombre = 'Falabella'")
