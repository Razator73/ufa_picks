"""cancelled-games

Revision ID: c4f9a1b7d2e0
Revises: b2c3d4e5f6a1
Create Date: 2026-07-23 00:00:00.000000

Adds a standalone table listing games that were cancelled. Games are refreshed
from an external source that overwrites the ``games`` table on every load, so
cancellations are tracked here (which the loader never touches) instead.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4f9a1b7d2e0"
down_revision = "b2c3d4e5f6a1"
branch_labels = None
depends_on = None

# Games known to be cancelled at the time of this migration.
INITIAL_CANCELLED_GAME_IDS = ["2026-07-18-PIT-CHI"]


def upgrade():
    cancelled_games = op.create_table(
        "cancelled_games",
        sa.Column("game_id", sa.String(length=18), nullable=False),
        sa.PrimaryKeyConstraint("game_id"),
    )
    op.bulk_insert(
        cancelled_games,
        [{"game_id": game_id} for game_id in INITIAL_CANCELLED_GAME_IDS],
    )


def downgrade():
    op.drop_table("cancelled_games")
