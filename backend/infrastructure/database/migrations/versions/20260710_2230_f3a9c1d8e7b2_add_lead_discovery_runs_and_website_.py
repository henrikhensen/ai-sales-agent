"""add lead discovery runs and website quality fields

Revision ID: f3a9c1d8e7b2
Revises: ea4064e30555
Create Date: 2026-07-10 22:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f3a9c1d8e7b2'
down_revision: Union[str, None] = 'ea4064e30555'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A temporary server_default backfills existing lead_candidates rows
    # with an empty list, matching the ORM/application default for new
    # rows — the same pattern used for user_feedback.priority in the prior
    # migration.
    op.add_column(
        'lead_candidates',
        sa.Column('website_quality_level', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'lead_candidates',
        sa.Column(
            'website_quality_reasons',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
        ),
    )
    op.alter_column('lead_candidates', 'website_quality_reasons', server_default=None)

    op.create_table(
        'lead_discovery_runs',
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('target_customer', sa.String(length=200), nullable=False),
        sa.Column('region', sa.String(length=200), nullable=True),
        sa.Column('offer_profile_id', sa.UUID(), nullable=True),
        sa.Column('icp_profile_id', sa.UUID(), nullable=True),
        sa.Column('requested_count', sa.Integer(), nullable=False),
        sa.Column('min_score', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('lead_sourcing_campaign_id', sa.UUID(), nullable=True),
        sa.Column('lead_sourcing_run_id', sa.UUID(), nullable=True),
        sa.Column('outreach_campaign_id', sa.UUID(), nullable=True),
        sa.Column('found_candidates', sa.Integer(), nullable=False),
        sa.Column('analyzed_websites', sa.Integer(), nullable=False),
        sa.Column('qualified_leads', sa.Integer(), nullable=False),
        sa.Column('rejected_leads', sa.Integer(), nullable=False),
        sa.Column('created_drafts', sa.Integer(), nullable=False),
        sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['offer_profile_id'], ['offer_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['icp_profile_id'], ['icp_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lead_sourcing_campaign_id'], ['lead_sourcing_campaigns.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lead_sourcing_run_id'], ['lead_sourcing_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['outreach_campaign_id'], ['outreach_campaigns.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_lead_discovery_runs_status'), 'lead_discovery_runs', ['status'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_lead_discovery_runs_status'), table_name='lead_discovery_runs')
    op.drop_table('lead_discovery_runs')
    op.drop_column('lead_candidates', 'website_quality_reasons')
    op.drop_column('lead_candidates', 'website_quality_level')
