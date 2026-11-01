"""El nombre canónico identifica al producto del catálogo: no se puede repetir.

Revision ID: 692c5b1aed02
Revises: cd893242420a
Create Date: 2026-11-01 12:12:14.001018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '692c5b1aed02'
down_revision: Union[str, Sequence[str], None] = 'cd893242420a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la restricción de unicidad."""
    op.create_unique_constraint(op.f('uq_producto_nombre_canonico'), 'producto', ['nombre_canonico'])


def downgrade() -> None:
    """Quita la restricción de unicidad."""
    op.drop_constraint(op.f('uq_producto_nombre_canonico'), 'producto', type_='unique')
