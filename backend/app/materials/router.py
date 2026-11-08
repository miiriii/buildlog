import asyncio
import anyio

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import ClientDisconnect

from app.accounts.dependencies import CurrentUser, DatabaseSession, require_csrf
from app.materials import storage
from app.materials.schemas import MaterialInput, MaterialList, MaterialOutput
from app.materials.responses import PRIVATE_HEADERS, PrivateFileResponse, PrivateMaterialRoute
from app.materials.services import create_material, delete_material, list_materials, read_original
from app.materials.services import find_owned
from app.materials.analysis_repository import configured, retry
from app.materials.analysis_schemas import AnalysisOutput, public_analysis

router = APIRouter(prefix="/api/materials", tags=["materials"], route_class=PrivateMaterialRoute)
MAX_BODY_BYTES = 32 * 1024 * 1024
UPLOAD_RECEIVE_SECONDS = 120


def notify_worker(request):
    try:
        request.app.state.analysis_worker.wake()
    except Exception:
        # The committed pending row is durable; periodic polling will find it.
        storage.logger.warning('Analysis notification deferred; saved material is preserved')


@router.get("", response_model=MaterialList)
def materials_list(request: Request, user: CurrentUser, session: DatabaseSession, response: Response):
    response.headers.update(PRIVATE_HEADERS)
    items = [MaterialOutput.model_validate(item) for item in list_materials(session, user.id)]
    if not configured(request.app.state.settings):
        for item in items:
            item.analysis.can_retry = False
    return {"items": items}


@router.get('/{material_id}/analysis', response_model=AnalysisOutput)
def material_analysis(material_id: int, request: Request, user: CurrentUser,
                      session: DatabaseSession, response: Response):
    response.headers.update(PRIVATE_HEADERS)
    return public_analysis(find_owned(session, user.id, material_id), configured(request.app.state.settings))


@router.post('/{material_id}/analysis/retry', status_code=202, response_model=AnalysisOutput)
async def retry_analysis(material_id: int, request: Request, user: CurrentUser,
                         session: DatabaseSession, response: Response, _csrf=Depends(require_csrf)):
    response.headers.update(PRIVATE_HEADERS)
    result = await run_in_threadpool(retry, session, user.id, material_id, request.app.state.settings)
    notify_worker(request)
    return result


@router.get("/{material_id}/file", response_class=PrivateFileResponse)
def material_original(material_id: int, request: Request, user: CurrentUser, session: DatabaseSession):
    stream, info, path, filename, mime_type = read_original(
        session, user.id, material_id, getattr(request.app.state, "uploads_root", storage.UPLOAD_ROOT),
    )
    try:
        return PrivateFileResponse(stream, info, path=path, filename=filename, mime_type=mime_type)
    except BaseException:
        stream.close()
        raise


@router.delete("/{material_id}", status_code=204)
def material_delete(material_id: int, request: Request, user: CurrentUser,
                    session: DatabaseSession, _csrf=Depends(require_csrf)):
    delete_material(session, user.id, material_id, getattr(request.app.state, "uploads_root", storage.UPLOAD_ROOT))
    return Response(status_code=204, headers=PRIVATE_HEADERS)


@router.post("", status_code=201, response_model=MaterialOutput, openapi_extra={
    "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
        "type": "object", "required": ["title", "file"], "properties": {
            "title": {"type": "string", "description": "앞뒤 공백 제거 후 1~100자"},
            "memo": {"type": "string", "maxLength": 1000},
            "file": {"type": "string", "format": "binary"},
        },
    }}}},
})
async def upload_material(request: Request, response: Response, user: CurrentUser,
                          session: DatabaseSession, _csrf=Depends(require_csrf)):
    response.headers["Cache-Control"] = "private, no-store"
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "multipart/form-data":
        raise HTTPException(415, "파일은 multipart/form-data 형식으로 보내 주세요.")
    length = request.headers.get("content-length")
    if length is not None:
        try:
            if int(length) < 0:
                raise ValueError
            if int(length) > MAX_BODY_BYTES:
                raise HTTPException(413, "업로드 요청이 최대 크기 32MiB를 초과했습니다.")
        except ValueError:
            raise HTTPException(422, "잘못된 요청 크기입니다.") from None
    total = 0

    async def bounded_receive():
        nonlocal total
        message = await request.receive()
        total += len(message.get("body", b""))
        if total > MAX_BODY_BYTES:
            raise HTTPException(413, "업로드 요청이 최대 크기 32MiB를 초과했습니다.")
        return message

    limited = Request(request.scope, receive=bounded_receive)
    try:
        async with asyncio.timeout(UPLOAD_RECEIVE_SECONDS):
            form = await limited.form(max_files=2, max_fields=3, max_part_size=16 * 1024)
        try:
            items = list(form.multi_items())
            if any(key not in {"title", "memo", "file"} for key, _ in items):
                raise HTTPException(422, "제목·메모·파일 한 개만 보내 주세요.")
            if (len(form.getlist("title")) != 1 or len(form.getlist("memo")) > 1
                    or len(form.getlist("file")) != 1
                    or sum(isinstance(value, UploadFile) for _, value in items) != 1
                    or not isinstance(form.get("file"), UploadFile)
                    or not isinstance(form.get("title"), str)
                    or not isinstance(form.get("memo", ""), str)):
                raise HTTPException(422, "제목과 파일 한 개, 선택 메모를 확인해 주세요.")
            try:
                data = MaterialInput(title=form["title"], memo=form.get("memo"))
            except ValidationError:
                raise HTTPException(422, "제목은 앞뒤 공백 제외 1~100자, 메모는 최대 1,000자로 입력해 주세요.") from None
            # Disk/Pillow/SQL operations stay off the event loop. The worker finishes
            # its commit or compensating cleanup before cancellation is propagated.
            result = await run_in_threadpool(
                create_material, session, user.id, data, form["file"],
                getattr(request.app.state, "uploads_root", storage.UPLOAD_ROOT),
                request.app.state.settings,
            )
            result.analysis.can_retry = result.analysis.can_retry and configured(request.app.state.settings)
            notify_worker(request)
            return result
        finally:
            with anyio.CancelScope(shield=True):
                await form.close()
    except TimeoutError:
        raise HTTPException(408, "파일 수신 시간이 초과되었습니다. 다시 선택해 주세요.") from None
    except ClientDisconnect:
        raise HTTPException(400, "파일 전송 연결이 끊어졌습니다.") from None
    except StarletteHTTPException as error:
        if error.status_code == 400:
            raise HTTPException(422, "업로드 항목이나 파일 개수를 확인해 주세요.") from None
        raise
    except OSError:
        raise HTTPException(503, "파일을 임시 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.") from None
