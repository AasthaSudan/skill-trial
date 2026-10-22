"""Resource metadata and permanent, versioned badge awards."""
from alembic import op
import sqlalchemy as sa

revision = '0002_resource_badge_features'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('learning_resources', sa.Column('details', sa.JSON(), nullable=False, server_default='{}'))
    op.add_column('badge_definitions', sa.Column('details', sa.JSON(), nullable=False, server_default='{}'))
    op.create_table('badge_awards',
        sa.Column('key', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('badge_slug', sa.String(), sa.ForeignKey('badge_definitions.slug'), nullable=False),
        sa.Column('tier', sa.Integer(), nullable=False),
        sa.Column('rule_version', sa.Integer(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('source', sa.JSON(), nullable=False),
        sa.Column('created', sa.Float(), nullable=False),
        sa.UniqueConstraint('user_id', 'badge_slug', 'tier'))
    op.create_index('ix_badge_awards_user_id', 'badge_awards', ['user_id'])
    op.create_index('ix_badge_awards_badge_slug', 'badge_awards', ['badge_slug'])

def downgrade():
    raise RuntimeError('Restore a verified backup instead of deleting earned badge history.')
