"""merge heads for email_verif and wg_client_id

Revision ID: 20250919_merge_heads
Revises: 20250916_email_verif, 20250918_add_wg_client_id
Create Date: 2025-09-18
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250919_merge_heads"
down_revision = ("20250916_email_verif", "20250918_add_wg_client_id")
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge-only migration. No DB operations are required; the
    # migration exists to make Alembic's linear history explicit.
    pass


def downgrade():
    # Downgrading a merge revision is non-trivial; disallow by raising.
    raise NotImplementedError("Cannot downgrade merge-only migration")
