"""Add durable private AI analysis state; existing materials are not queued."""
from alembic import op
import sqlalchemy as sa

revision = '0003_material_analysis'
down_revision = '0002_materials'
branch_labels = depends_on = None

def columns():
    return [
        sa.Column('analysis_status', sa.String(20), nullable=False, server_default='not_requested'),
        sa.Column('analysis_summary', sa.Text()), sa.Column('analysis_error_code', sa.String(64)),
        sa.Column('analysis_model', sa.String(100)), sa.Column('analysis_prompt_version', sa.String(40)),
        sa.Column('analysis_started_at', sa.DateTime(timezone=True)), sa.Column('analysis_completed_at', sa.DateTime(timezone=True)),
        sa.Column('analysis_job_token', sa.String(36)), sa.Column('analysis_lease_expires_at', sa.DateTime(timezone=True)),
        sa.Column('analysis_attempt_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('analysis_version', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('analysis_input_tokens', sa.BigInteger()), sa.Column('analysis_output_tokens', sa.BigInteger()),
        sa.Column('analysis_metadata', sa.JSON(none_as_null=True)),
    ]

checks = {
    'analysis_status': "analysis_status IN ('not_requested','pending','processing','succeeded','failed')",
    'analysis_counts': 'analysis_attempt_count BETWEEN 0 AND 3 AND analysis_version >= 0',
    'analysis_usage': '(analysis_input_tokens IS NULL OR analysis_input_tokens >= 0) AND (analysis_output_tokens IS NULL OR analysis_output_tokens >= 0)',
    'analysis_summary': "(analysis_status = 'succeeded' AND length(trim(analysis_summary)) BETWEEN 1 AND 2000 AND analysis_summary IS NOT NULL AND analysis_error_code IS NULL AND analysis_completed_at IS NOT NULL) OR (analysis_status != 'succeeded' AND analysis_summary IS NULL)",
    'analysis_failure': "analysis_status != 'failed' OR (analysis_error_code IS NOT NULL AND analysis_completed_at IS NOT NULL)",
    'analysis_pending': "analysis_status != 'pending' OR (analysis_error_code IS NULL AND analysis_completed_at IS NULL)",
    'analysis_lease': "(analysis_status = 'processing' AND analysis_job_token IS NOT NULL AND analysis_started_at IS NOT NULL AND analysis_lease_expires_at IS NOT NULL) OR (analysis_status != 'processing' AND analysis_job_token IS NULL AND analysis_lease_expires_at IS NULL)",
}
indexes = {'ix_materials_analysis_queue': ['analysis_status', 'created_at', 'id'],
           'ix_materials_analysis_owner': ['owner_id', 'analysis_status'],
           'ix_materials_analysis_expiry': ['analysis_status', 'analysis_lease_expires_at']}

def upgrade():
    # ALTER COLUMN ADD is supported by SQLite without replacing referenced tables.
    for column in columns():
        op.add_column('materials', column)
    with op.batch_alter_table('materials') as batch:
        for name, condition in checks.items():
            batch.create_check_constraint(op.f('ck_materials_' + name), condition)
        for name, fields in indexes.items():
            batch.create_index(name, fields)

def downgrade():
    with op.batch_alter_table('materials') as batch:
        for name in indexes:
            batch.drop_index(name)
        for name in checks:
            batch.drop_constraint(op.f('ck_materials_' + name), type_='check')
        for column in reversed(columns()):
            batch.drop_column(column.name)
