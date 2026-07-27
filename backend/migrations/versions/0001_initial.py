"""Initial schema with PostGIS location index."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    game_status = sa.Enum("active", "complete", "expired", name="gamestatus")
    location_status = sa.Enum("active", "stale", "deleted", name="locationstatus")
    op.create_table(
        "games",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("status", game_status, nullable=False),
        sa.Column("current_round", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_games_session_id", "games", ["session_id"])
    op.create_index("ix_games_created_at", "games", ["created_at"])
    op.create_index("ix_games_expires_at", "games", ["expires_at"])
    op.create_table(
        "playable_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("image_id", sa.String(128), nullable=False, unique=True),
        sa.Column("sequence_id", sa.String(128)),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("compass_angle", sa.Float()),
        sa.Column("quality", sa.Float(), nullable=False),
        sa.Column("status", location_status, nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("metadata_fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_selected_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_playable_locations_country_code", "playable_locations", ["country_code"])
    op.create_index("ix_playable_locations_status", "playable_locations", ["status"])
    op.create_index(
        "ix_location_country_status_quality",
        "playable_locations",
        ["country_code", "status", "quality"],
    )
    op.execute(
        "CREATE INDEX ix_playable_locations_geography ON playable_locations "
        "USING GIST ((ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography))"
    )
    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "game_id",
            postgresql.UUID(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            sa.Integer(),
            sa.ForeignKey("playable_locations.id"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("guessed", sa.Boolean(), nullable=False),
        sa.Column("guess_latitude", sa.Float()),
        sa.Column("guess_longitude", sa.Float()),
        sa.Column("distance_km", sa.Float()),
        sa.Column("score", sa.Integer()),
        sa.Column("guessed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("game_id", "number"),
    )
    op.create_index("ix_rounds_game_id", "rounds", ["game_id"])
    op.create_table(
        "country_catalog",
        sa.Column("country_code", sa.String(2), primary_key=True),
        sa.Column("active_count", sa.Integer(), nullable=False),
        sa.Column("last_refilled_at", sa.DateTime(timezone=True)),
        sa.Column("provider_cursor", sa.String(512)),
    )
    op.create_table(
        "provider_state",
        sa.Column("provider", sa.String(32), primary_key=True),
        sa.Column("circuit_open_until", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("provider_state")
    op.drop_table("country_catalog")
    op.drop_table("rounds")
    op.drop_table("playable_locations")
    op.drop_table("games")
    op.execute("DROP TYPE IF EXISTS locationstatus")
    op.execute("DROP TYPE IF EXISTS gamestatus")
