"""
Initial migration — создаёт таблицы payments и outbox.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- payments ---
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("amount", postgresql.NUMERIC(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.Enum("RUB", "USD", "EUR", name="currency", create_type=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.Enum("pending", "succeeded", "failed", name="paymentstatus", create_type=True), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("webhook_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        sa.Index("ix_payments_idempotency_key", "idempotency_key", unique=True),
    )

    # --- outbox ---
    op.create_table(
        "outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Enum("pending", "published", name="outboxstatus", create_type=True), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Index("ix_outbox_status_created_at", "status", "created_at"),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("outbox")
    op.execute("DROP TYPE IF EXISTS outboxstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS currency")
