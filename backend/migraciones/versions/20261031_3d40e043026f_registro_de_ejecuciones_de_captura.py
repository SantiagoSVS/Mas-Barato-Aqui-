"""Registro de ejecuciones de captura por plataforma (errores y estado, RNF-05).

Revision ID: 3d40e043026f
Revises: 587238317b91
Create Date: 2026-10-31 14:41:30.023021

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d40e043026f'
down_revision: Union[str, Sequence[str], None] = '587238317b91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea la tabla ejecucion_captura."""
    op.create_table('ejecucion_captura',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('plataforma_id', sa.Integer(), nullable=False),
    sa.Column('iniciada_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('terminada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('ofertas_capturadas', sa.Integer(), server_default='0', nullable=False),
    sa.Column('errores', sa.Integer(), server_default='0', nullable=False),
    sa.Column('mensaje_error', sa.Text(), nullable=True),
    sa.CheckConstraint("estado IN ('en_curso', 'exitosa', 'parcial', 'fallida')", name=op.f('ck_ejecucion_captura_estado_valido')),
    sa.ForeignKeyConstraint(['plataforma_id'], ['plataforma.id'], name=op.f('fk_ejecucion_captura_plataforma_id_plataforma')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ejecucion_captura'))
    )
    op.create_index('ix_ejecucion_captura_plataforma_id_iniciada_en', 'ejecucion_captura', ['plataforma_id', 'iniciada_en'], unique=False)


def downgrade() -> None:
    """Elimina la tabla ejecucion_captura."""
    op.drop_index('ix_ejecucion_captura_plataforma_id_iniciada_en', table_name='ejecucion_captura')
    op.drop_table('ejecucion_captura')
