"""Переименовывает колонку metadata → extra_data в payments.

Revision ID: 002_rename_metadata_to_extra_data
Revises: 001_initial
Create Date: 2026-10-20
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "002_extra_data"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "payments",
        "metadata",
        new_column_name="extra_data",
    )


def downgrade() -> None:
    op.alter_column(
        "payments",
        "extra_data",
        new_column_name="metadata",
    )