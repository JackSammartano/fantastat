"""add player merge audit

Revision ID: a81f5d4c2e10
Revises: d37bd727689e
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a81f5d4c2e10"
down_revision: str | None = "d37bd727689e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "player_merge_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("source_player_id", sa.Integer(), nullable=False),
        sa.Column("target_player_id", sa.Integer(), nullable=False),
        sa.Column("moved_stats_ids", sa.JSON(), nullable=False),
        sa.Column("moved_alias_ids", sa.JSON(), nullable=False),
        sa.Column("moved_current_list_ids", sa.JSON(), nullable=False),
        sa.Column("previous_statuses", sa.JSON(), nullable=False),
        sa.Column("preview_token", sa.String(64), nullable=False),
        sa.Column("backup_path", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reverted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('applied','reverted')",
            name="ck_player_merge_audits_status",
        ),
        sa.ForeignKeyConstraint(["review_id"], ["player_mapping_reviews.id"]),
        sa.ForeignKeyConstraint(["source_player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["target_player_id"], ["players.id"]),
        sa.UniqueConstraint("review_id", name="uq_player_merge_audits_review"),
    )


def downgrade() -> None:
    op.drop_table("player_merge_audits")
