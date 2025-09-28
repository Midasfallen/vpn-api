"""add wg_config_encrypted to vpn_peers

Revision ID: 20250928_add_wg_config_encrypted
Revises: 20250919_merge_heads
Create Date: 2025-09-28
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250928_add_wg_config_encrypted"
down_revision = "20250919_merge_heads"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("vpn_peers") as batch_op:
        batch_op.add_column(sa.Column("wg_config_encrypted", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("vpn_peers") as batch_op:
        batch_op.drop_column("wg_config_encrypted")
