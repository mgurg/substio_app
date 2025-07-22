"""create places table

Revision ID: 2548fc10b15b
Revises: 2dbc4a162767
Create Date: 2025-07-22 14:38:36.443729

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2548fc10b15b'
down_revision: Union[str, Sequence[str], None] = '2dbc4a162767'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "places",
        sa.Column("id", sa.INTEGER(), sa.Identity(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("uuid", sa.VARCHAR(length=36), autoincrement=False, nullable=True),
        sa.Column('name', sa.TEXT(), nullable=False),
        sa.Column('name_ascii', sa.TEXT(), nullable=False),
        sa.Column('category', sa.TEXT(), nullable=False),
        sa.Column('lat', sa.Numeric(precision=10, scale=7), nullable=True, index=True),
        sa.Column('lon', sa.Numeric(precision=10, scale=7), nullable=True, index=True),
        sa.Column('street_name', sa.TEXT(), nullable=True),
        sa.Column('street_number', sa.TEXT(), nullable=True),
        sa.Column('city', sa.TEXT(), nullable=False),
        sa.Column('state_province', sa.TEXT(), nullable=True),
        sa.Column('postal_code', sa.TEXT(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("places")
