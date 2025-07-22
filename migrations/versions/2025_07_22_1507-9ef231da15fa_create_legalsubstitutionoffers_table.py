"""create LegalSubstitutionOffers table

Revision ID: 9ef231da15fa
Revises: 2548fc10b15b
Create Date: 2025-07-22 15:07:27.267007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ef231da15fa'
down_revision: Union[str, Sequence[str], None] = '2548fc10b15b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'legal_substitution_offers',
        sa.Column("id", sa.INTEGER(), sa.Identity(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("uuid", sa.VARCHAR(length=36), autoincrement=False, nullable=True),
        sa.Column('place_id', sa.TEXT(), nullable=True),
        sa.Column('place_name', sa.TEXT(), nullable=True),
        sa.Column('user_id', sa.TEXT(), nullable=True),
        sa.Column('user_name', sa.TEXT(), nullable=True),
        sa.Column('email', sa.TEXT(), nullable=True),
        sa.Column('url', sa.TEXT(), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('hour', sa.Time(), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('invoice', sa.Boolean(), nullable=True),
        sa.Column('status',  sa.Text(), nullable=True),
        sa.Column('valid_to', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("legal_substitution_offers")
