"""initial tables

Revision ID: 0001_initial
Revises: 
Create Date: 2025-11-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем, существует ли таблица chats
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'chats' not in tables:
        op.create_table(
            'chats',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('chat_id', sa.BigInteger(), nullable=False),
            sa.Column('chat_type', sa.String(length=20), nullable=False),
            sa.Column('chat_title', sa.String(length=255)),
            sa.Column('added_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('chat_id', name='uq_chats_chat_id'),
        )
        op.create_index('ix_chats_chat_id', 'chats', ['chat_id'], unique=False)
    else:
        # Таблица существует, проверяем индекс
        indexes = [idx['name'] for idx in inspector.get_indexes('chats')]
        if 'ix_chats_chat_id' not in indexes:
            op.create_index('ix_chats_chat_id', 'chats', ['chat_id'], unique=False)

    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('full_name', sa.String(length=255), nullable=False),
            sa.Column('department', sa.String(length=255), nullable=False),
            sa.Column('telegram_username', sa.String(length=255), nullable=True),
            sa.Column('telegram_id', sa.BigInteger(), nullable=True),
            sa.Column('birth_date', sa.String(length=10), nullable=True),
            sa.Column('faculty', sa.String(length=255), nullable=True),
            sa.Column('course', sa.Integer(), nullable=True),
            sa.Column('study_group', sa.String(length=50), nullable=True),
            sa.Column('phone_number', sa.String(length=20), nullable=True),
            sa.Column('has_car', sa.String(length=255), nullable=True),
            sa.Column('nearest_metro', sa.Text(), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_users_full_name', 'users', ['full_name'], unique=False)
        op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=False)
    else:
        indexes = [idx['name'] for idx in inspector.get_indexes('users')]
        if 'ix_users_full_name' not in indexes:
            op.create_index('ix_users_full_name', 'users', ['full_name'], unique=False)
        if 'ix_users_telegram_id' not in indexes:
            op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=False)

    if 'quotes' not in tables:
        op.create_table(
            'quotes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('chat_id', sa.BigInteger(), nullable=False),
            sa.Column('author_user_id', sa.BigInteger(), nullable=False),
            sa.Column('author_name', sa.String(length=255), nullable=True),
            sa.Column('quoter_user_id', sa.BigInteger(), nullable=False),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_quotes_chat_id', 'quotes', ['chat_id'], unique=False)
        op.create_index('ix_quotes_author_user_id', 'quotes', ['author_user_id'], unique=False)
        op.create_index('ix_quotes_quoter_user_id', 'quotes', ['quoter_user_id'], unique=False)
        op.create_index('ix_quotes_created_at', 'quotes', ['created_at'], unique=False)
    else:
        indexes = [idx['name'] for idx in inspector.get_indexes('quotes')]
        for idx_name, col_name in [('ix_quotes_chat_id', 'chat_id'), ('ix_quotes_author_user_id', 'author_user_id'), 
                                    ('ix_quotes_quoter_user_id', 'quoter_user_id'), ('ix_quotes_created_at', 'created_at')]:
            if idx_name not in indexes:
                op.create_index(idx_name, 'quotes', [col_name], unique=False)

    if 'beer_stats' not in tables:
        op.create_table(
            'beer_stats',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('chat_id', sa.BigInteger(), nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('username', sa.String(length=255), nullable=True),
            sa.Column('count', sa.Integer(), nullable=False, default=0),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_beer_stats_chat_id', 'beer_stats', ['chat_id'], unique=False)
        op.create_index('ix_beer_stats_user_id', 'beer_stats', ['user_id'], unique=False)
    else:
        indexes = [idx['name'] for idx in inspector.get_indexes('beer_stats')]
        if 'ix_beer_stats_chat_id' not in indexes:
            op.create_index('ix_beer_stats_chat_id', 'beer_stats', ['chat_id'], unique=False)
        if 'ix_beer_stats_user_id' not in indexes:
            op.create_index('ix_beer_stats_user_id', 'beer_stats', ['user_id'], unique=False)

    if 'wakeups' not in tables:
        op.create_table(
            'wakeups',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('chat_id', sa.BigInteger(), nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('wake_at', sa.DateTime(), nullable=False),
            sa.Column('done', sa.Boolean(), nullable=False, default=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_wakeups_chat_id', 'wakeups', ['chat_id'], unique=False)
        op.create_index('ix_wakeups_user_id', 'wakeups', ['user_id'], unique=False)
        op.create_index('ix_wakeups_wake_at', 'wakeups', ['wake_at'], unique=False)
        op.create_index('ix_wakeups_done', 'wakeups', ['done'], unique=False)
    else:
        indexes = [idx['name'] for idx in inspector.get_indexes('wakeups')]
        for idx_name, col_name in [('ix_wakeups_chat_id', 'chat_id'), ('ix_wakeups_user_id', 'user_id'),
                                    ('ix_wakeups_wake_at', 'wake_at'), ('ix_wakeups_done', 'done')]:
            if idx_name not in indexes:
                op.create_index(idx_name, 'wakeups', [col_name], unique=False)


def downgrade() -> None:
    op.drop_index('ix_wakeups_done', table_name='wakeups')
    op.drop_index('ix_wakeups_wake_at', table_name='wakeups')
    op.drop_index('ix_wakeups_user_id', table_name='wakeups')
    op.drop_index('ix_wakeups_chat_id', table_name='wakeups')
    op.drop_table('wakeups')

    op.drop_index('ix_beer_stats_user_id', table_name='beer_stats')
    op.drop_index('ix_beer_stats_chat_id', table_name='beer_stats')
    op.drop_table('beer_stats')

    op.drop_index('ix_quotes_created_at', table_name='quotes')
    op.drop_index('ix_quotes_quoter_user_id', table_name='quotes')
    op.drop_index('ix_quotes_author_user_id', table_name='quotes')
    op.drop_index('ix_quotes_chat_id', table_name='quotes')
    op.drop_table('quotes')

    op.drop_index('ix_users_telegram_id', table_name='users')
    op.drop_index('ix_users_full_name', table_name='users')
    op.drop_table('users')

    op.drop_index('ix_chats_chat_id', table_name='chats')
    op.drop_table('chats')


