"""Short, independent transactions; no request Session crosses into a job."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.materials.analysis_schemas import public_analysis
from app.materials.models import Material
from app.materials.services import find_owned


def configured(settings):
    return settings.analysis_enabled and bool(settings.openai_api_key.get_secret_value().strip())


def lock_owner(session, owner_id, *, skip_locked=False):
    return session.scalar(select(User.id).where(User.id == owner_id).with_for_update(skip_locked=skip_locked))


def queue_full(session, owner_id):
    return session.scalar(select(func.count()).select_from(Material).where(
        Material.owner_id == owner_id, Material.analysis_status == 'pending')) >= 2


def initialize(session, material, settings):
    if not settings.analysis_enabled:
        return
    lock_owner(session, material.owner_id)
    code = 'missing_key' if not configured(settings) else ('queue_full' if queue_full(session, material.owner_id) else None)
    material.analysis_status = 'failed' if code else 'pending'
    material.analysis_error_code = code
    material.analysis_completed_at = datetime.now(UTC) if code else None
    material.analysis_version = 1


def retry(session, owner_id, material_id, settings):
    lock_owner(session, owner_id)
    material = find_owned(session, owner_id, material_id, lock=True)
    if not configured(settings):
        raise HTTPException(503, 'backend/.env의 OPENAI_API_KEY 설정과 서버 재시작을 확인해 주세요.')
    if material.analysis_status != 'failed' or material.analysis_attempt_count >= 3:
        raise HTTPException(409, '실패한 분석만 최대 3회까지 실행할 수 있습니다.')
    if queue_full(session, owner_id):
        raise HTTPException(429, '대기 중인 분석이 많습니다. 잠시 후 다시 시도해 주세요.')
    material.analysis_status = 'pending'
    material.analysis_error_code = None
    material.analysis_completed_at = None
    material.analysis_version += 1
    result = public_analysis(material)
    session.commit()
    return result


def claim(engine, settings):
    now = datetime.now(UTC)
    with Session(engine) as session, session.begin():
        # An expired job never returns to pending automatically: avoid duplicate billing.
        session.execute(update(Material).where(Material.analysis_status == 'processing',
            Material.analysis_lease_expires_at <= now).values(analysis_status='failed',
            analysis_error_code='interrupted', analysis_completed_at=now,
            analysis_job_token=None, analysis_lease_expires_at=None,
            analysis_version=Material.analysis_version + 1))
    with Session(engine, expire_on_commit=False) as session, session.begin():
        candidates = session.scalars(select(Material).where(Material.analysis_status == 'pending')
            .order_by(Material.created_at, Material.id).limit(20)).all()
        for item in candidates:
            if lock_owner(session, item.owner_id, skip_locked=True) is None:
                continue
            active = session.scalar(select(func.count()).select_from(Material).where(
                Material.owner_id == item.owner_id, Material.analysis_status == 'processing'))
            if active:
                continue
            token = str(uuid4())
            changed = session.execute(update(Material).where(Material.id == item.id,
                Material.analysis_status == 'pending', Material.analysis_attempt_count < 3).values(
                analysis_status='processing', analysis_job_token=token,
                analysis_started_at=now, analysis_lease_expires_at=now + timedelta(seconds=settings.analysis_lease_seconds),
                analysis_attempt_count=Material.analysis_attempt_count + 1,
                analysis_version=Material.analysis_version + 1))
            if changed.rowcount:
                return dict(id=item.id, owner_id=item.owner_id, token=token,
                    stored_filename=item.stored_filename, media_type=item.media_type,
                    title=item.title, memo=item.memo)
    return None


def finish(engine, job, *, code=None, result=None, model=None):
    now = datetime.now(UTC)
    values = dict(analysis_status='failed' if code else 'succeeded', analysis_error_code=code,
        analysis_completed_at=now, analysis_job_token=None, analysis_lease_expires_at=None,
        analysis_version=Material.analysis_version + 1)
    if result:
        values.update(analysis_summary=result['summary'], analysis_metadata=result['scope'],
            analysis_model=model, analysis_prompt_version='materials-summary-v1',
            analysis_input_tokens=result.get('input_tokens'), analysis_output_tokens=result.get('output_tokens'))
    with Session(engine) as session, session.begin():
        return session.execute(update(Material).where(Material.id == job['id'],
            Material.owner_id == job['owner_id'], Material.analysis_status == 'processing',
            Material.analysis_job_token == job['token'], Material.analysis_lease_expires_at > now)
            .values(**values)).rowcount == 1


def still_current(engine, job):
    with Session(engine) as session:
        return session.scalar(select(Material.id).where(Material.id == job['id'],
            Material.owner_id == job['owner_id'], Material.analysis_status == 'processing',
            Material.analysis_job_token == job['token'],
            Material.analysis_lease_expires_at > datetime.now(UTC))) is not None
