"""per-user stats cache (item_stats) + dirty queue filled by triggers; content_items.series_key

The triggers make sure EVERY change to word_knowledge (reader, import, Anki, quizzes, rebuild) marks the items that
contain the word as dirty, without any code path having to remember it.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# items (in the word's language) that contain the lemma
AFFECTED = """
    INSERT OR IGNORE INTO stats_dirty (user_id, item_id)
    SELECT DISTINCT {row}.user_id, w.item_id
    FROM content_word_lemmas l
    JOIN content_words w ON w.id = l.word_id
    JOIN content_items i ON i.id = w.item_id AND i.language = {row}.language
    WHERE l.lemma = {row}.lemma;
"""

TRIGGERS = {
    'trg_knowledge_insert': f'AFTER INSERT ON word_knowledge BEGIN {AFFECTED.format(row="NEW")} END',
    'trg_knowledge_update': f'AFTER UPDATE OF state ON word_knowledge WHEN OLD.state IS NOT NEW.state '
    f'BEGIN {AFFECTED.format(row="NEW")} END',
    'trg_knowledge_delete': f'AFTER DELETE ON word_knowledge BEGIN {AFFECTED.format(row="OLD")} END',
}


def upgrade() -> None:
    with op.batch_alter_table('content_items') as b:
        b.add_column(sa.Column('series_key', sa.String(length=300), nullable=False, server_default=''))
        b.create_index('ix_content_series_key', ['series_key'])
    op.create_table(
        'item_stats',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('content_items.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('sentences', sa.Integer(), nullable=False),
        sa.Column('words_total', sa.Integer(), nullable=False),
        sa.Column('words_known', sa.Integer(), nullable=False),
        sa.Column('new_words', sa.Integer(), nullable=False),
        sa.Column('one_new', sa.Integer(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'stats_dirty',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('content_items.id', ondelete='CASCADE'), primary_key=True),
    )
    for name, body in TRIGGERS.items():
        op.execute(f'CREATE TRIGGER {name} {body}')
    # everything analysed so far needs its stats computed once
    op.execute(
        'INSERT INTO stats_dirty (user_id, item_id) SELECT u.id, i.id FROM users u, content_items i '
        "WHERE i.status = 'analyzed'"
    )


def downgrade() -> None:
    for name in TRIGGERS:
        op.execute(f'DROP TRIGGER IF EXISTS {name}')
    op.drop_table('stats_dirty')
    op.drop_table('item_stats')
    with op.batch_alter_table('content_items') as b:
        b.drop_index('ix_content_series_key')
        b.drop_column('series_key')
