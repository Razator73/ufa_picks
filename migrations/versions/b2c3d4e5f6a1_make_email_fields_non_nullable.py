"""Populate and make email reminder fields non-nullable

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-04-08 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a1'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Populate existing rows before enforcing NOT NULL
    op.execute("UPDATE users SET get_email_reminder = FALSE WHERE get_email_reminder IS NULL")
    op.execute("UPDATE users SET force_password_change = FALSE WHERE force_password_change IS NULL")

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('get_email_reminder', nullable=False)
        batch_op.alter_column('force_password_change', nullable=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('get_email_reminder', nullable=True)
        batch_op.alter_column('force_password_change', nullable=True)
