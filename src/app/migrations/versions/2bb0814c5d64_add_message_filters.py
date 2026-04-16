"""add message filters table

Revision ID: 2bb0814c5d64
Revises: ae553cec1ef5
Create Date: 2026-04-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2bb0814c5d64'
down_revision: Union[str, Sequence[str], None] = 'ae553cec1ef5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'message_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_row_id', sa.Integer(), nullable=False),
        sa.Column('filter_name', sa.String(), nullable=False),
        sa.Column('filter_value', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['message_row_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_row_id', 'filter_name')
    )
    op.create_index('idx_message_filters_message_row_id', 'message_filters', ['message_row_id'], unique=False)
    op.create_index('idx_message_filters_filter_name', 'message_filters', ['filter_name'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_message_filters_filter_name', table_name='message_filters')
    op.drop_index('idx_message_filters_message_row_id', table_name='message_filters')
    op.drop_table('message_filters')
