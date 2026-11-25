"""content library: items, sentences, words, lemmas, occurrences

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'content_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('language', sa.String(length=8), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('external_id', sa.String(length=500), nullable=False),
        sa.Column('series', sa.String(length=300), nullable=False),
        sa.Column('season', sa.Integer(), nullable=True),
        sa.Column('episode', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('path', sa.String(length=1000), nullable=False),
        sa.Column('duration_s', sa.Float(), nullable=True),
        sa.Column('subtitle', sa.String(length=300), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('detail', sa.String(length=500), nullable=True),
        sa.Column('analyzer', sa.String(length=32), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('source', 'external_id', name='uq_content_source_external'),
    )
    op.create_table(
        'content_sentences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('content_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('idx', sa.Integer(), nullable=False),
        sa.Column('start_ms', sa.Integer(), nullable=False),
        sa.Column('end_ms', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.UniqueConstraint('item_id', 'idx', name='uq_sentence_item_idx'),
    )
    op.create_table(
        'content_words',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('content_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(length=200), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('weak', sa.Boolean(), nullable=False),
        sa.Column('first_idx', sa.Integer(), nullable=False),
        sa.UniqueConstraint('item_id', 'key', name='uq_word_item_key'),
    )
    op.create_table(
        'content_word_lemmas',
        sa.Column('word_id', sa.Integer(), sa.ForeignKey('content_words.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('lemma', sa.String(length=200), primary_key=True),
        sa.Column('ord', sa.Integer(), nullable=False),
    )
    op.create_index('ix_word_lemmas_lemma', 'content_word_lemmas', ['lemma'])
    op.create_table(
        'content_occurrences',
        sa.Column(
            'sentence_id', sa.Integer(), sa.ForeignKey('content_sentences.id', ondelete='CASCADE'), primary_key=True
        ),
        sa.Column('word_id', sa.Integer(), sa.ForeignKey('content_words.id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('content_occurrences')
    op.drop_index('ix_word_lemmas_lemma', table_name='content_word_lemmas')
    op.drop_table('content_word_lemmas')
    op.drop_table('content_words')
    op.drop_table('content_sentences')
    op.drop_table('content_items')
