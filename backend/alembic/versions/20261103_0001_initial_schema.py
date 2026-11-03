"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-11-03 17:21:10.445362
"""

from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('candidates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('external_ref', sa.String(length=32), nullable=True),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('experience_years', sa.Float(), nullable=False),
    sa.Column('profile_summary', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('experience_years >= 0', name=op.f('ck_candidates_experience_non_negative')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_candidates')),
    sa.UniqueConstraint('external_ref', name=op.f('uq_candidates_external_ref'))
    )
    with op.batch_alter_table('candidates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_candidates_email'), ['email'], unique=True)

    op.create_table('jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('external_ref', sa.String(length=32), nullable=True),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('min_experience_years', sa.Float(), nullable=False),
    sa.Column('version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('min_experience_years >= 0', name=op.f('ck_jobs_min_experience_non_negative')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_jobs')),
    sa.UniqueConstraint('external_ref', name=op.f('uq_jobs_external_ref'))
    )
    op.create_table('skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_skills')),
    sa.UniqueConstraint('name', name=op.f('uq_skills_name'))
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('role', sa.String(length=32), server_default='recruiter', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('applications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('external_ref', sa.String(length=32), nullable=True),
    sa.Column('candidate_id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default='Applied', nullable=False),
    sa.Column('version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('Applied', 'Shortlisted', 'Rejected')", name=op.f('ck_applications_status_allowed')),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name=op.f('fk_applications_candidate_id_candidates')),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], name=op.f('fk_applications_job_id_jobs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_applications')),
    sa.UniqueConstraint('candidate_id', 'job_id', name='uq_applications_candidate_job'),
    sa.UniqueConstraint('external_ref', name=op.f('uq_applications_external_ref'))
    )
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.create_index('ix_applications_job_id', ['job_id'], unique=False)
        batch_op.create_index('ix_applications_status', ['status'], unique=False)

    op.create_table('audit_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entity_type', sa.String(length=32), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=32), nullable=False),
    sa.Column('before_json', sa.JSON(), nullable=True),
    sa.Column('after_json', sa.JSON(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_audit_log_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.create_index('ix_audit_log_entity', ['entity_type', 'entity_id'], unique=False)

    op.create_table('candidate_skills',
    sa.Column('candidate_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name=op.f('fk_candidate_skills_candidate_id_candidates')),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], name=op.f('fk_candidate_skills_skill_id_skills')),
    sa.PrimaryKeyConstraint('candidate_id', 'skill_id', name=op.f('pk_candidate_skills'))
    )
    op.create_table('job_skills',
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.CheckConstraint("kind IN ('required', 'preferred')", name=op.f('ck_job_skills_kind_allowed')),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], name=op.f('fk_job_skills_job_id_jobs')),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], name=op.f('fk_job_skills_skill_id_skills')),
    sa.PrimaryKeyConstraint('job_id', 'skill_id', name=op.f('pk_job_skills'))
    )
    op.create_table('predictions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.Column('label', sa.String(length=32), nullable=False),
    sa.Column('probability', sa.Float(), nullable=False),
    sa.Column('model_version', sa.String(length=64), nullable=False),
    sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("label IN ('Potential Match', 'Needs Review')", name=op.f('ck_predictions_label_allowed')),
    sa.CheckConstraint('probability >= 0 AND probability <= 1', name=op.f('ck_predictions_probability_range')),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name=op.f('fk_predictions_application_id_applications'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_predictions')),
    sa.UniqueConstraint('application_id', name=op.f('uq_predictions_application_id'))
    )
    op.create_table('status_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.Column('old_status', sa.String(length=16), nullable=False),
    sa.Column('new_status', sa.String(length=16), nullable=False),
    sa.Column('changed_by_user_id', sa.Integer(), nullable=False),
    sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name=op.f('fk_status_history_application_id_applications')),
    sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], name=op.f('fk_status_history_changed_by_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_status_history'))
    )
    with op.batch_alter_table('status_history', schema=None) as batch_op:
        batch_op.create_index('ix_status_history_application_id', ['application_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('status_history', schema=None) as batch_op:
        batch_op.drop_index('ix_status_history_application_id')

    op.drop_table('status_history')
    op.drop_table('predictions')
    op.drop_table('job_skills')
    op.drop_table('candidate_skills')
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_log_entity')

    op.drop_table('audit_log')
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.drop_index('ix_applications_status')
        batch_op.drop_index('ix_applications_job_id')

    op.drop_table('applications')
    op.drop_table('users')
    op.drop_table('skills')
    op.drop_table('jobs')
    with op.batch_alter_table('candidates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_candidates_email'))

    op.drop_table('candidates')
