"""add math_duels table

Revision ID: 0002_add_math_duels
Revises: 0001_initial
Create Date: 2025-11-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '0002_add_math_duels'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем, существует ли таблица math_duels
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'math_duels' not in tables:
        op.create_table(
            'math_duels',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('chat_id', sa.BigInteger(), nullable=False),
            sa.Column('user1_id', sa.BigInteger(), nullable=False),
            sa.Column('user2_id', sa.BigInteger(), nullable=False),
            sa.Column('num1', sa.Integer(), nullable=False),
            sa.Column('num2', sa.Integer(), nullable=False),
            sa.Column('correct_answer', sa.Integer(), nullable=False),
            sa.Column('winner_id', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('expired', sa.Boolean(), nullable=False, default=False),
        )
        op.create_index('ix_math_duels_chat_id', 'math_duels', ['chat_id'], unique=False)
        op.create_index('ix_math_duels_created_at', 'math_duels', ['created_at'], unique=False)
        op.create_index('ix_math_duels_expired', 'math_duels', ['expired'], unique=False)
    else:
        # Таблица существует, проверяем индексы
        indexes = [idx['name'] for idx in inspector.get_indexes('math_duels')]
        for idx_name, col_name in [('ix_math_duels_chat_id', 'chat_id'), 
                                    ('ix_math_duels_created_at', 'created_at'),
                                    ('ix_math_duels_expired', 'expired')]:
            if idx_name not in indexes:
                op.create_index(idx_name, 'math_duels', [col_name], unique=False)


def downgrade() -> None:
    op.drop_index('ix_math_duels_expired', table_name='math_duels')
    op.drop_index('ix_math_duels_created_at', table_name='math_duels')
    op.drop_index('ix_math_duels_chat_id', table_name='math_duels')
    op.drop_table('math_duels')

