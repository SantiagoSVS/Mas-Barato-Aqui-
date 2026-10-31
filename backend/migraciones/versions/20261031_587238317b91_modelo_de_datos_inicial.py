"""Modelo de datos inicial: las 6 tablas de la sección 6 del documento de arquitectura.

Revision ID: 587238317b91
Revises: 
Create Date: 2026-10-31 09:17:52.838155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '587238317b91'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea las tablas, índices y restricciones."""
    op.create_table('consulta',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('texto_original', sa.String(length=300), nullable=False),
    sa.Column('criterios', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('confianza', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('tiempo_respuesta_ms', sa.Integer(), nullable=True),
    sa.Column('tokens_consumidos', sa.Integer(), nullable=True),
    sa.Column('con_cobertura', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_consulta'))
    )
    op.create_table('plataforma',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.Column('tipo_acceso', sa.String(length=20), nullable=False),
    sa.Column('url_base', sa.String(length=255), nullable=False),
    sa.Column('moneda', sa.String(length=3), nullable=False),
    sa.Column('activa', sa.Boolean(), server_default='true', nullable=False),
    sa.CheckConstraint("tipo_acceso IN ('api', 'extraccion')", name=op.f('ck_plataforma_tipo_acceso_valido')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_plataforma')),
    sa.UniqueConstraint('nombre', name=op.f('uq_plataforma_nombre'))
    )
    op.create_table('producto',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre_canonico', sa.String(length=255), nullable=False),
    sa.Column('marca', sa.String(length=80), nullable=True),
    sa.Column('modelo', sa.String(length=120), nullable=True),
    sa.Column('categoria', sa.String(length=80), nullable=False),
    sa.Column('atributos', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_producto'))
    )
    op.create_table('oferta',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('plataforma_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=True),
    sa.Column('titulo_original', sa.Text(), nullable=False),
    sa.Column('url_origen', sa.Text(), nullable=False),
    sa.Column('vendedor', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['plataforma_id'], ['plataforma.id'], name=op.f('fk_oferta_plataforma_id_plataforma')),
    sa.ForeignKeyConstraint(['producto_id'], ['producto.id'], name=op.f('fk_oferta_producto_id_producto')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oferta')),
    sa.UniqueConstraint('plataforma_id', 'url_origen', name=op.f('uq_oferta_plataforma_id_url_origen'))
    )
    op.create_index(op.f('ix_oferta_producto_id'), 'oferta', ['producto_id'], unique=False)
    op.create_table('captura',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('oferta_id', sa.Integer(), nullable=False),
    sa.Column('capturado_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('precio_cop', sa.BigInteger(), nullable=False),
    sa.Column('envio_cop', sa.BigInteger(), nullable=True),
    sa.Column('dias_entrega', sa.Integer(), nullable=True),
    sa.Column('disponible', sa.Boolean(), nullable=False),
    sa.Column('precio_original', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('moneda_original', sa.String(length=3), nullable=True),
    sa.Column('tasa_cambio', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.CheckConstraint('(precio_original IS NULL AND moneda_original IS NULL AND tasa_cambio IS NULL) OR (precio_original IS NOT NULL AND moneda_original IS NOT NULL AND tasa_cambio IS NOT NULL)', name=op.f('ck_captura_conversion_completa')),
    sa.CheckConstraint('dias_entrega IS NULL OR dias_entrega >= 0', name=op.f('ck_captura_dias_no_negativos')),
    sa.CheckConstraint('envio_cop IS NULL OR envio_cop >= 0', name=op.f('ck_captura_envio_no_negativo')),
    sa.CheckConstraint('precio_cop >= 0', name=op.f('ck_captura_precio_no_negativo')),
    sa.ForeignKeyConstraint(['oferta_id'], ['oferta.id'], name=op.f('fk_captura_oferta_id_oferta')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_captura'))
    )
    op.create_index('ix_captura_oferta_id_capturado_en', 'captura', ['oferta_id', 'capturado_en'], unique=False)
    op.create_table('recomendacion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('consulta_id', sa.Integer(), nullable=False),
    sa.Column('oferta_id', sa.Integer(), nullable=False),
    sa.Column('posicion', sa.Integer(), nullable=False),
    sa.Column('costo_total_cop', sa.BigInteger(), nullable=False),
    sa.Column('componentes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['consulta_id'], ['consulta.id'], name=op.f('fk_recomendacion_consulta_id_consulta')),
    sa.ForeignKeyConstraint(['oferta_id'], ['oferta.id'], name=op.f('fk_recomendacion_oferta_id_oferta')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recomendacion'))
    )
    op.create_index(op.f('ix_recomendacion_consulta_id'), 'recomendacion', ['consulta_id'], unique=False)


def downgrade() -> None:
    """Elimina las tablas en orden inverso a sus dependencias."""
    op.drop_index(op.f('ix_recomendacion_consulta_id'), table_name='recomendacion')
    op.drop_table('recomendacion')
    op.drop_index('ix_captura_oferta_id_capturado_en', table_name='captura')
    op.drop_table('captura')
    op.drop_index(op.f('ix_oferta_producto_id'), table_name='oferta')
    op.drop_table('oferta')
    op.drop_table('producto')
    op.drop_table('plataforma')
    op.drop_table('consulta')
