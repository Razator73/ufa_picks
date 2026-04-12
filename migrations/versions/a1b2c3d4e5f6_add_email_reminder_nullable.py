"""Add email reminder and force password change (nullable)

Revision ID: a1b2c3d4e5f6
Revises: 51c898e45023
Create Date: 2026-04-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '51c898e45023'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('get_email_reminder', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('force_password_change', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('force_password_change')
        batch_op.drop_column('get_email_reminder')
