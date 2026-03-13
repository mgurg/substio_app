"""add indexes and unique constraints

Revision ID: 5eb23b10c9d9
Revises: 73a219a8e6b8
Create Date: 2026-03-13 15:55:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5eb23b10c9d9'
down_revision: Union[str, Sequence[str], None] = '73a219a8e6b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add indexes to offers table
    op.create_index(op.f('ix_offers_status'), 'offers', ['status'], unique=False)
    op.create_index(op.f('ix_offers_valid_to'), 'offers', ['valid_to'], unique=False)
    op.create_index(op.f('ix_offers_created_at'), 'offers', ['created_at'], unique=False)
    op.create_index(op.f('ix_offers_offer_uid'), 'offers', ['offer_uid'], unique=False)
    op.create_index(op.f('ix_offers_email'), 'offers', ['email'], unique=False)

    # Add unique constraints and indexes to uuid columns
    op.create_index(op.f('ix_offers_uuid'), 'offers', ['uuid'], unique=True)
    op.create_index(op.f('ix_legal_roles_uuid'), 'legal_roles', ['uuid'], unique=True)
    op.create_index(op.f('ix_places_uuid'), 'places', ['uuid'], unique=True)
    op.create_index(op.f('ix_cities_uuid'), 'cities', ['uuid'], unique=True)


def downgrade() -> None:
    # Drop indexes from uuid columns
    op.drop_index(op.f('ix_cities_uuid'), table_name='cities')
    op.drop_index(op.f('ix_places_uuid'), table_name='places')
    op.drop_index(op.f('ix_legal_roles_uuid'), table_name='legal_roles')
    op.drop_index(op.f('ix_offers_uuid'), table_name='offers')

    # Drop indexes from offers table
    op.drop_index(op.f('ix_offers_email'), table_name='offers')
    op.drop_index(op.f('ix_offers_offer_uid'), table_name='offers')
    op.drop_index(op.f('ix_offers_created_at'), table_name='offers')
    op.drop_index(op.f('ix_offers_valid_to'), table_name='offers')
    op.drop_index(op.f('ix_offers_status'), table_name='offers')
