"""Create the initial user table."""
from alembic import op
import sqlalchemy as sa

revision = "0001_users"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("nickname", sa.String(20), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint("length(email) BETWEEN 3 AND 320", name=op.f("ck_users_email_length")),
        sa.CheckConstraint("email = trim(email)", name=op.f("ck_users_email_trimmed")),
        sa.CheckConstraint("length(nickname) BETWEEN 2 AND 20", name=op.f("ck_users_nickname_length")),
        sa.CheckConstraint("nickname = trim(nickname)", name=op.f("ck_users_nickname_trimmed")),
        sa.CheckConstraint("password_hash LIKE '$argon2id$%'", name=op.f("ck_users_password_hash_format")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("nickname", name=op.f("uq_users_nickname")),
    )


def downgrade():
    op.drop_table("users")
