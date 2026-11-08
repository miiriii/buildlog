from contextlib import asynccontextmanager

import anyio
from fastapi import HTTPException
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse

PRIVATE_HEADERS = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}


class PrivateMaterialRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def private_handler(request):
            try:
                response = await handler(request)
            except StarletteHTTPException as error:
                error.headers = {**(error.headers or {}), **PRIVATE_HEADERS}
                raise
            except SQLAlchemyError:
                raise HTTPException(503, "처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                                    headers=PRIVATE_HEADERS) from None
            response.headers.update(PRIVATE_HEADERS)
            return response

        return private_handler


class PrivateFileResponse(FileResponse):
    """Stream the already opened, authorized file, including byte ranges."""

    def __init__(self, stream, info, *, path, filename, mime_type):
        self.stream = stream
        super().__init__(path, filename=filename, media_type=mime_type, stat_result=info,
                         content_disposition_type="inline", headers=PRIVATE_HEADERS)

    @asynccontextmanager
    async def _open_file(self):
        # FileResponse uses this once for simple, single and multiple range responses.
        file = anyio.wrap_file(self.stream)
        try:
            yield file
        finally:
            with anyio.CancelScope(shield=True):
                await file.aclose()

    async def __call__(self, scope, receive, send):
        # Disable path-send: serving by path would reopen a file after permission checks.
        scope = dict(scope, extensions={k: v for k, v in scope.get("extensions", {}).items()
                                       if k != "http.response.pathsend"})

        async def private_send(message):
            if message["type"] == "http.response.start":
                # Starlette's malformed/unsatisfiable range responses also need these.
                headers = [(k, v) for k, v in message.get("headers", [])
                           if k.lower() not in (b"cache-control", b"x-content-type-options")]
                message = dict(message, headers=headers + [
                    (b"cache-control", b"private, no-store"), (b"x-content-type-options", b"nosniff"),
                ])
            await send(message)

        try:
            await super().__call__(scope, receive, private_send)
        finally:
            # Includes range errors, disconnects and header-only responses.
            self.stream.close()
