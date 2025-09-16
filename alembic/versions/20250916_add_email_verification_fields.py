"""add email verification fields to users

Revision ID: 20250916_add_email_verification_fields
Revises:
Create Date: 2025-09-16
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250916_add_email_verification_fields"
down_revision = "881faf8bfb76"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("verification_code", sa.String(length=255), nullable=True))
    op.add_column(
        "users", sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        op.f("ix_users_verification_code"), "users", ["verification_code"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_users_verification_code"), table_name="users")
    op.drop_column("users", "verification_expires_at")
    op.drop_column("users", "verification_code")
    op.drop_column("users", "is_verified")
