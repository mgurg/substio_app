"""create LegalRoles table

Revision ID: 73a219a8e6b8
Revises: 9ef231da15fa
Create Date: 2025-07-25 13:12:17.662543

"""
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '73a219a8e6b8'
down_revision: Union[str, Sequence[str], None] = '9ef231da15fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'legal_roles',
        sa.Column("id", sa.INTEGER(), sa.Identity(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('name', sa.TEXT(), nullable=False),
        sa.Column('symbol', sa.TEXT(), nullable=False),
    )

    legal_roles_table = sa.table(
        'legal_roles',
        sa.column('uuid', postgresql.UUID(as_uuid=True)),
        sa.column('name', sa.TEXT),
        sa.column('symbol', sa.TEXT),
    )

    op.bulk_insert(legal_roles_table, [
        {'uuid': uuid4(), 'name': 'Adwokat', 'symbol': 'ADW'},
        {'uuid': uuid4(), 'name': 'Radca prawny', 'symbol': 'RPR'},
        {'uuid': uuid4(), 'name': 'Aplikant adwokacki', "symbol": "APL_ADW"},
        {'uuid': uuid4(), 'name': 'Aplikant radcowski', "symbol": "APL_RPR"},
        # {'uuid': uuid4(), 'name': 'Komornik', "symbol": "KOM"},
    ])

    op.create_table(
        'offers_legal_roles_link',
        sa.Column('offer_id', sa.INTEGER(), sa.ForeignKey('offers.id', ), nullable=False),
        sa.Column('legal_role_id', sa.INTEGER(), sa.ForeignKey('legal_roles.id', ), nullable=False),
        sa.PrimaryKeyConstraint('offer_id', 'legal_role_id'),
    )


def downgrade() -> None:
    # Drop table
    op.drop_table('offers_legal_roles_link')
    op.drop_table('legal_roles')
