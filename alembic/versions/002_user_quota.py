"""Add user quota fields and activation codes

Revision ID: 002_user_quota
Revises: 001_initial
Create Date: 2024-12-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_user_quota'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === 用户表添加配额字段 ===
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='free'))
    op.add_column('users', sa.Column('daily_quota', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('users', sa.Column('bonus_quota', sa.Integer(), nullable=False, server_default='0'))
    
    # === 激活码表 ===
    op.create_table(
        'activation_codes',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('code', sa.String(32), nullable=False),
        sa.Column('code_type', sa.String(20), nullable=False),
        sa.Column('quota_value', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['used_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        comment='激活码表'
    )
    op.create_index('ix_activation_codes_code', 'activation_codes', ['code'], unique=True)
    
    # === 使用记录表 ===
    op.create_table(
        'usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('guest_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('destination', sa.String(100), nullable=True),
        sa.Column('days', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['guest_id'], ['guests.id'], ),
        comment='使用记录表'
    )
    op.create_index('ix_usage_records_user_id', 'usage_records', ['user_id'])
    op.create_index('ix_usage_records_guest_id', 'usage_records', ['guest_id'])
    op.create_index('ix_usage_records_usage_date', 'usage_records', ['usage_date'])
    
    # === 每日使用汇总表 ===
    op.create_table(
        'daily_usage_summary',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('guest_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['guest_id'], ['guests.id'], ),
        comment='每日使用汇总表'
    )
    op.create_index('ix_daily_usage_summary_user_id', 'daily_usage_summary', ['user_id'])
    op.create_index('ix_daily_usage_summary_guest_id', 'daily_usage_summary', ['guest_id'])
    op.create_index('ix_daily_usage_summary_usage_date', 'daily_usage_summary', ['usage_date'])


def downgrade() -> None:
    # 删除表
    op.drop_table('daily_usage_summary')
    op.drop_table('usage_records')
    op.drop_table('activation_codes')
    
    # 删除用户表的新字段
    op.drop_column('users', 'bonus_quota')
    op.drop_column('users', 'daily_quota')
    op.drop_column('users', 'role')
