"""Add avatar_url to users and image_url to leagues

Revision ID: 010_images_and_urls
Revises: 009_football_prediction_source
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "010_images_and_urls"
down_revision = "009_football_prediction_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users",   sa.Column("avatar_url",  sa.String(500), nullable=True))
    op.add_column("leagues", sa.Column("image_url",   sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("users",   "avatar_url")
    op.drop_column("leagues", "image_url")
