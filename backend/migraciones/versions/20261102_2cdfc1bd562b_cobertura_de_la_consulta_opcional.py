"""consulta.con_cobertura admite vacío: la consulta que requiere aclaración no llega a buscarse.

Revision ID: 2cdfc1bd562b
Revises: 4d4c10d25b7b
Create Date: 2026-11-02 11:22:23.877577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cdfc1bd562b'
down_revision: Union[str, Sequence[str], None] = '4d4c10d25b7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Permite vacío en consulta.con_cobertura."""
    op.alter_column('consulta', 'con_cobertura',
               existing_type=sa.BOOLEAN(),
               nullable=True)


def downgrade() -> None:
    """Vuelve a exigir el valor (requiere que no haya filas vacías)."""
    op.alter_column('consulta', 'con_cobertura',
               existing_type=sa.BOOLEAN(),
               nullable=False)
