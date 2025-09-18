"""add wg_client_id to vpn_peers

Revision ID: 20250918_add_wg_client_id
Revises: 881faf8bfb76
Create Date: 2025-09-18
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250918_add_wg_client_id"
down_revision = "881faf8bfb76"
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable wg_client_id column to vpn_peers for external controller tracking
    with op.batch_alter_table("vpn_peers") as batch_op:
        batch_op.add_column(sa.Column("wg_client_id", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("vpn_peers") as batch_op:
        batch_op.drop_column("wg_client_id")
