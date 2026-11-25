"""users, knowledge events, word knowledge

Revision ID: 0001
Revises:
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'knowledge_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('language', sa.String(length=8), nullable=False),
        sa.Column('lemma', sa.String(length=200), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_events_user_lang_lemma', 'knowledge_events', ['user_id', 'language', 'lemma'])
    op.create_table(
        'word_knowledge',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('language', sa.String(length=8), nullable=False),
        sa.Column('lemma', sa.String(length=200), nullable=False),
        sa.Column('state', sa.String(length=16), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'language', 'lemma', name='uq_knowledge_user_lang_lemma'),
    )


def downgrade() -> None:
    op.drop_table('word_knowledge')
    op.drop_index('ix_events_user_lang_lemma', table_name='knowledge_events')
    op.drop_table('knowledge_events')
    op.drop_table('users')
