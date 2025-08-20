def downgrade():
##
# Auto-generated Alembic migration template.
#
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '${up_revision}'
down_revision = ${repr(down_revision) if down_revision else None}
branch_labels = ${repr(branch_labels) if branch_labels else None}
depends_on = ${repr(depends_on) if depends_on else None}


def upgrade():
% if upgrade_ops:
% for stmt in upgrade_ops:
    ${stmt}
% endfor
% else:
    pass
% endif


def downgrade():
% if downgrade_ops:
% for stmt in downgrade_ops:
    ${stmt}
% endfor
% else:
    pass
% endif
