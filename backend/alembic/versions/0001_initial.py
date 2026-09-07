"""Initial schema."""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(12), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(300), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("capacity > 0", name="ck_dive_capacity_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_dives_public_id", "dives", ["public_id"])
    op.create_index("ix_dives_starts_at", "dives", ["starts_at"])
    op.create_table(
        "officers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "inventory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "category", sa.Enum("wetsuit", "fins", "mask", "weight_set", name="gearcategory")
        ),
        sa.Column("suit_size", sa.Enum("XS", "S", "M", "L", "XL", name="suitsize")),
        sa.Column("min_shoe_size", sa.Float()),
        sa.Column("max_shoe_size", sa.Float()),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_inventory_quantity"),
        sa.CheckConstraint(
            "min_shoe_size IS NULL OR max_shoe_size IS NULL OR min_shoe_size <= max_shoe_size",
            name="ck_fin_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_category", "inventory", ["category"])
    op.create_table(
        "signups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dive_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column(
            "status", sa.Enum("confirmed", "waitlisted", name="signupstatus"), nullable=False
        ),
        sa.Column("queue_order", sa.Integer(), nullable=False),
        sa.Column("needs_carpool", sa.Boolean(), nullable=False),
        sa.Column("pickup_location", sa.String(300)),
        sa.Column("needs_gear", sa.Boolean(), nullable=False),
        sa.Column("suit_size", sa.Enum("XS", "S", "M", "L", "XL", name="suitsize")),
        sa.Column("shoe_size", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "shoe_size IS NULL OR (shoe_size >= 1 AND shoe_size <= 18)", name="ck_shoe"
        ),
        sa.ForeignKeyConstraint(["dive_id"], ["dives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dive_id", "email", name="uq_signup_dive_email"),
    )
    op.create_index("ix_signup_queue", "signups", ["dive_id", "status", "queue_order"])
    op.create_table(
        "dive_officers",
        sa.Column("dive_id", sa.Uuid(), nullable=False),
        sa.Column("officer_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["dive_id"], ["dives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["officer_id"], ["officers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("dive_id", "officer_id"),
    )
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_attempts_ip_hash", "login_attempts", ["ip_hash"])
    op.create_index("ix_login_attempts_attempted_at", "login_attempts", ["attempted_at"])


def downgrade() -> None:
    op.drop_table("login_attempts")
    op.drop_table("dive_officers")
    op.drop_table("signups")
    op.drop_table("inventory")
    op.drop_table("officers")
    op.drop_table("dives")
