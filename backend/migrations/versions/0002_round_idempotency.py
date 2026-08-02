"""Persist idempotency keys for concurrency-safe guess submission."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rounds", sa.Column("idempotency_key", postgresql.UUID(), nullable=True))
    op.create_unique_constraint("uq_rounds_idempotency_key", "rounds", ["idempotency_key"])


def downgrade():
    op.drop_constraint("uq_rounds_idempotency_key", "rounds", type_="unique")
    op.drop_column("rounds", "idempotency_key")
