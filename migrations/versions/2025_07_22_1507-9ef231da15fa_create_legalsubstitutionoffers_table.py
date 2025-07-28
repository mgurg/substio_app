"""create LegalSubstitutionOffers table

Revision ID: 9ef231da15fa
Revises: 2548fc10b15b
Create Date: 2025-07-22 15:07:27.267007

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9ef231da15fa'
down_revision: Union[str, Sequence[str], None] = '2548fc10b15b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'offers',
        sa.Column("id", sa.INTEGER(), sa.Identity(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("uuid", sa.VARCHAR(length=36), autoincrement=False, nullable=True),
        sa.Column('place_id', sa.TEXT(), nullable=True),
        sa.Column('place_name', sa.TEXT(), nullable=True),
        sa.Column('email', sa.TEXT(), nullable=True),
        sa.Column('url', sa.TEXT(), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('hour', sa.Time(), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('invoice', sa.Boolean(), nullable=True),
        sa.Column('status', sa.Text(), nullable=True),
        sa.Column('visible', sa.Boolean(), nullable=True),
        sa.Column('raw_data', sa.Text(), nullable=True),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('author', sa.TEXT(), nullable=True),
        sa.Column('author_uid', sa.TEXT(), nullable=True),
        sa.Column('offer_uid', sa.TEXT(), nullable=True),
        sa.Column('added_at', sa.DateTime()),
        sa.Column('valid_to', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("offers")
