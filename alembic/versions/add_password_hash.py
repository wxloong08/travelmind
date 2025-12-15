"""Add password_hash to users table

Revision ID: add_password_hash
Revises: 002_user_quota
Create Date: 2025-12-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_password_hash'
down_revision: Union[str, None] = '002_user_quota'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 password_hash 列到 users 表
    op.add_column(
        'users',
        sa.Column('password_hash', sa.String(128), nullable=True, comment='密码哈希（bcrypt）')
    )


def downgrade() -> None:
    # 移除 password_hash 列
    op.drop_column('users', 'password_hash')
