"""Add signup phone and driving details."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("signups") as batch_op:
        batch_op.add_column(sa.Column("phone", sa.String(32), nullable=True))
        batch_op.add_column(
            sa.Column("can_drive", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("available_seats", sa.Integer(), nullable=True))

    op.execute("UPDATE signups SET phone = 'Not provided' WHERE phone IS NULL")

    with op.batch_alter_table("signups") as batch_op:
        batch_op.alter_column(
            "phone", existing_type=sa.String(32), nullable=False
        )
        batch_op.create_check_constraint(
            "ck_signup_driver_seats",
            "(can_drive AND available_seats BETWEEN 1 AND 20) "
            "OR (NOT can_drive AND available_seats IS NULL)",
        )
        batch_op.create_check_constraint(
            "ck_signup_carpool_or_driver", "NOT (needs_carpool AND can_drive)"
        )
        batch_op.alter_column(
            "can_drive", existing_type=sa.Boolean(), nullable=False, server_default=None
        )


def downgrade() -> None:
    with op.batch_alter_table("signups") as batch_op:
        batch_op.drop_constraint("ck_signup_carpool_or_driver", type_="check")
        batch_op.drop_constraint("ck_signup_driver_seats", type_="check")
        batch_op.drop_column("available_seats")
        batch_op.drop_column("can_drive")
        batch_op.drop_column("phone")
