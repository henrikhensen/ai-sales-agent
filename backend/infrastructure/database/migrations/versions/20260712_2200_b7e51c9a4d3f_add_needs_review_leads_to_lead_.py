"""add needs_review_leads to lead discovery runs

Revision ID: b7e51c9a4d3f
Revises: f3a9c1d8e7b2
Create Date: 2026-07-12 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e51c9a4d3f'
down_revision: Union[str, None] = 'f3a9c1d8e7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Distinguishes "needs_review" qualification outcomes (real candidate,
    # score/data just not trustworthy enough yet) from true rejections
    # (disqualified/blocked/duplicate) — previously both were folded into
    # rejected_leads, making a run with only needs_review candidates read
    # as "0 qualified, all rejected" even though every candidate was still
    # visible and actionable ("zu prüfen").
    op.add_column(
        'lead_discovery_runs',
        sa.Column(
            'needs_review_leads',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
    )
    op.alter_column('lead_discovery_runs', 'needs_review_leads', server_default=None)


def downgrade() -> None:
    op.drop_column('lead_discovery_runs', 'needs_review_leads')
