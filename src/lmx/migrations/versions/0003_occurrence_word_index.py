"""index content_occurrences(word_id): the 1T count looks occurrences up by word (0.75 s -> 0.09 s for 20 episodes)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index('ix_occurrences_word', 'content_occurrences', ['word_id'])


def downgrade() -> None:
    op.drop_index('ix_occurrences_word', table_name='content_occurrences')
