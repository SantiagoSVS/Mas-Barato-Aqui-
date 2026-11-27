"""Desactiva Mercado Libre: desde el 20 de noviembre de 2026 su API ya no entrega los precios.

Las rutas que dan el precio de las publicaciones (/products/{id}/items, /items, /sites/MCO/search)
responden 403 a aplicaciones de terceros, con token de aplicación y con token de usuario, aun con
todos los permisos funcionales activos (prueba del 27 de noviembre de 2026). Falabella y Homecenter
quedan como tiendas principales. El historial de Mercado Libre se conserva y la plataforma se
puede reactivar si Mercado Libre vuelve a dar acceso.

Revision ID: 9a3f1c2b7d40
Revises: 2cdfc1bd562b
Create Date: 2026-11-27 10:00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9a3f1c2b7d40'
down_revision: Union[str, Sequence[str], None] = '2cdfc1bd562b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Deja la plataforma inactiva: el worker no la captura y la interfaz no la lista."""
    op.execute("UPDATE plataforma SET activa = false WHERE nombre = 'Mercado Libre'")


def downgrade() -> None:
    """La vuelve a activar."""
    op.execute("UPDATE plataforma SET activa = true WHERE nombre = 'Mercado Libre'")
