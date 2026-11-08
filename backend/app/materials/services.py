from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.materials import storage
from app.materials.models import Material
from app.materials.schemas import MaterialOutput


def create_material(session, owner_id, data, upload, root, settings=None):
    pending = final = None
    promoted = False
    try:
        pending, final, metadata = storage.stage_file(upload, root, owner_id)
        material = Material(owner_id=owner_id, title=data.title, memo=data.memo, **metadata)
        if settings is not None:
            from app.materials.analysis_repository import initialize
            initialize(session, material, settings)
        session.add(material)
        session.flush()
        # Validate the safe response before committing; don't refresh after commit.
        result = MaterialOutput.model_validate(material)
        storage.promote_file(pending, final)
        promoted = True
        session.commit()
    except BaseException as error:
        try:
            session.rollback()
        finally:
            storage.remove_owned(pending)
            if promoted:
                storage.remove_owned(final)
        if isinstance(error, (OSError, SQLAlchemyError)):
            raise HTTPException(503, "자료를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.") from None
        raise
    storage.remove_owned(pending)
    return result


def find_owned(session, owner_id, material_id, *, lock=False):
    statement = select(Material).where(Material.id == material_id, Material.owner_id == owner_id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    material = session.scalar(statement)
    if material is None:
        raise HTTPException(404, "자료를 찾을 수 없습니다.")
    return material


def list_materials(session, owner_id):
    return session.scalars(select(Material).where(Material.owner_id == owner_id)
                           .order_by(Material.created_at.desc(), Material.id.desc())).all()


def read_original(session, owner_id, material_id, root):
    material = find_owned(session, owner_id, material_id)
    try:
        path = storage.material_path(root, owner_id, material.stored_filename)
        stream, info = storage.open_original(path)
    except FileNotFoundError:
        raise HTTPException(404, "자료를 찾을 수 없습니다.") from None
    except OSError:
        raise HTTPException(503, "원본 파일을 열지 못했습니다. 잠시 후 다시 시도해 주세요.") from None
    return stream, info, path, material.original_filename, material.mime_type


def delete_material(session, owner_id, material_id, root):
    quarantined = original = None
    try:
        material = find_owned(session, owner_id, material_id, lock=True)
        original = storage.material_path(root, owner_id, material.stored_filename)
        quarantined = storage.quarantine_file(original, root)
        session.delete(material)
        session.commit()
    except BaseException as error:
        try:
            session.rollback()
        finally:
            if quarantined is not None:
                try:
                    storage.restore_file(quarantined, original)
                except OSError:
                    storage.logger.error("Material delete recovery failed; storage reconciliation required")
        if isinstance(error, (OSError, SQLAlchemyError)):
            raise HTTPException(503, "자료를 삭제하지 못했습니다. 잠시 후 다시 시도해 주세요.") from None
        raise
    # Once the row is committed, this file has no public API path. A failed purge
    # is an internal reconciliation task, not a failed user deletion.
    storage.remove_owned(quarantined)
