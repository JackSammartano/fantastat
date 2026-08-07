"""Add all official current-list valuation fields.

Revision ID: f14c20262701
Revises: a81f5d4c2e10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f14c20262701"
down_revision: Union[str, None] = "a81f5d4c2e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("current_season_list") as batch_op:
        batch_op.add_column(sa.Column("initial_quotation", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("mantra_quotation", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column("initial_mantra_quotation", sa.Float(), nullable=True)
        )
        batch_op.add_column(sa.Column("fvm", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("fvm_mantra", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("current_season_list") as batch_op:
        batch_op.drop_column("fvm_mantra")
        batch_op.drop_column("fvm")
        batch_op.drop_column("initial_mantra_quotation")
        batch_op.drop_column("mantra_quotation")
        batch_op.drop_column("initial_quotation")
