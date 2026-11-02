"""Aviso de envío por plataforma, para tiendas que no dejan cotizarlo.

Revision ID: faa6744ca824
Revises: 692c5b1aed02
Create Date: 2026-11-01 12:43:09.941759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'faa6744ca824'
down_revision: Union[str, Sequence[str], None] = '692c5b1aed02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la columna plataforma.nota_envio."""
    op.add_column('plataforma', sa.Column('nota_envio', sa.Text(), nullable=True))


def downgrade() -> None:
    """Quita la columna plataforma.nota_envio."""
    op.drop_column('plataforma', 'nota_envio')
