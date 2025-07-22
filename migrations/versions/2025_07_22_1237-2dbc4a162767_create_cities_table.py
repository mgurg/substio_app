"""create cities table

Revision ID: 2dbc4a162767
Revises: 
Create Date: 2025-07-22 12:37:48.737211

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2dbc4a162767'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("id", sa.INTEGER(), sa.Identity(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("uuid", sa.VARCHAR(length=36), autoincrement=False, nullable=True),
        sa.Column('name', sa.TEXT(), nullable=False),
        sa.Column('name_ascii', sa.TEXT(), nullable=False),
        sa.Column('lat', sa.Numeric(precision=10, scale=7), nullable=True, index=True),
        sa.Column('lon', sa.Numeric(precision=10, scale=7), nullable=True, index=True),
        sa.Column('lat_min', sa.Numeric(precision=10, scale=7), nullable=True),  # South Latitude
        sa.Column('lat_max', sa.Numeric(precision=10, scale=7), nullable=True),  # North Latitude
        sa.Column('lon_min', sa.Numeric(precision=10, scale=7), nullable=True),  # West Longitude
        sa.Column('lon_max', sa.Numeric(precision=10, scale=7), nullable=True),  # East Longitude
        sa.Column('population', sa.Integer(), nullable=True),
        sa.Column('importance', sa.Float(), nullable=True),
        sa.Column('category', sa.TEXT(), nullable=False),
        sa.Column('region', sa.TEXT(), nullable=True),
        sa.Column('in_title', sa.TEXT(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("cities")
