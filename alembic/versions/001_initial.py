"""Initial migration - create user system tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-12-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === 用户表 ===
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('wechat_openid', sa.String(64), nullable=True),
        sa.Column('nickname', sa.String(50), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('preferences', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='注册用户表'
    )
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
    op.create_index('ix_users_wechat_openid', 'users', ['wechat_openid'], unique=True)

    # === 游客表 ===
    op.create_table(
        'guests',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('device_fingerprint', sa.String(64), nullable=False),
        sa.Column('daily_usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_usage_date', sa.Date(), nullable=True),
        sa.Column('total_usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='游客表'
    )
    op.create_index('ix_guests_device_fingerprint', 'guests', ['device_fingerprint'], unique=True)

    # === 行程表 ===
    op.create_table(
        'trips',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('guest_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('destination', sa.String(50), nullable=False),
        sa.Column('days', sa.Integer(), nullable=False),
        sa.Column('travel_date', sa.Date(), nullable=True),
        sa.Column('user_budget', sa.Integer(), nullable=True),
        sa.Column('estimated_budget', sa.Integer(), nullable=True),
        sa.Column('itinerary_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.Column('weather_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('pois_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guest_id'], ['guests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='行程表'
    )
    op.create_index('ix_trips_user_id', 'trips', ['user_id'])
    op.create_index('ix_trips_guest_id', 'trips', ['guest_id'])
    op.create_index('ix_trips_destination', 'trips', ['destination'])

    # === 对话表 ===
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('guest_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('session_id', sa.String(64), nullable=False),
        sa.Column('trip_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('title', sa.String(100), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guest_id'], ['guests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='对话表'
    )
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_guest_id', 'conversations', ['guest_id'])
    op.create_index('ix_conversations_session_id', 'conversations', ['session_id'])

    # === 消息表 ===
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='消息表'
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('trips')
    op.drop_table('guests')
    op.drop_table('users')
