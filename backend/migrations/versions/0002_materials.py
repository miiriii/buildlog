"""Add private material metadata without changing users."""
from alembic import op
import sqlalchemy as sa

revision = "0002_materials"
down_revision = "0001_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("memo", sa.String(1000), nullable=True),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(5), nullable=False),
        sa.Column("mime_type", sa.String(32), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_materials")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_materials_owner_id_users")),
        sa.UniqueConstraint("stored_filename", name=op.f("uq_materials_stored_filename")),
        sa.CheckConstraint("length(title) BETWEEN 1 AND 100", name=op.f("ck_materials_title_length")),
        sa.CheckConstraint("title = trim(title)", name=op.f("ck_materials_title_trimmed")),
        sa.CheckConstraint("memo IS NULL OR length(memo) BETWEEN 1 AND 1000", name=op.f("ck_materials_memo_length")),
        sa.CheckConstraint("length(original_filename) > 0", name=op.f("ck_materials_original_filename_length")),
        sa.CheckConstraint("length(stored_filename) BETWEEN 1 AND 255", name=op.f("ck_materials_stored_filename_length")),
        sa.CheckConstraint("media_type IN ('image', 'video')", name=op.f("ck_materials_media_type")),
        sa.CheckConstraint("mime_type IN ('image/png', 'image/jpeg', 'video/mp4')", name=op.f("ck_materials_mime_type")),
        sa.CheckConstraint(
            "(media_type = 'image' AND mime_type IN ('image/png', 'image/jpeg') "
            "AND size_bytes BETWEEN 1 AND 5242880) OR "
            "(media_type = 'video' AND mime_type = 'video/mp4' "
            "AND size_bytes BETWEEN 1 AND 31457280)", name=op.f("ck_materials_type_size"),
        ),
    )
    op.create_index("ix_materials_owner_created_id", "materials", ["owner_id", "created_at", "id"])
    if op.get_context().dialect.name == "postgresql":
        # Cookie identity is checked by FastAPI, not Supabase Auth policies.
        # Table owner/backend remains able to query; Data API roles get no access.
        op.execute("ALTER TABLE materials ENABLE ROW LEVEL SECURITY")
        op.execute("REVOKE ALL PRIVILEGES ON TABLE materials FROM PUBLIC")
        op.execute("REVOKE ALL PRIVILEGES ON SEQUENCE materials_id_seq FROM PUBLIC")
        op.execute("""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL PRIVILEGES ON TABLE materials FROM anon;
        REVOKE ALL PRIVILEGES ON SEQUENCE materials_id_seq FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL PRIVILEGES ON TABLE materials FROM authenticated;
        REVOKE ALL PRIVILEGES ON SEQUENCE materials_id_seq FROM authenticated;
    END IF;
END;
$$
""")


def downgrade():
    op.drop_index("ix_materials_owner_created_id", table_name="materials")
    op.drop_table("materials")
