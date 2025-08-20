# Alembic migration script
revision = 'init'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('email', sa.String, unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String, nullable=False),
        sa.Column('status', sa.String, default='pending'),
        sa.Column('is_admin', sa.Boolean, default=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now()),
    )
    op.create_table(
        'tariffs',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String, unique=True, nullable=False),
        sa.Column('price', sa.Integer, nullable=False),
    )
    op.create_table(
        'user_tariffs',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('tariff_id', sa.Integer, sa.ForeignKey('tariffs.id'), nullable=False, index=True),
        sa.Column('started_at', sa.TIMESTAMP, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('user_tariffs')
    op.drop_table('tariffs')
    op.drop_table('users')
