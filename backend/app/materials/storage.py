"""Local private storage. No static serving or user-controlled storage paths."""
import logging
import os
import re
import stat
import struct
import tempfile
import uuid
import warnings
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from app.core.config import BACKEND_ROOT

UPLOAD_ROOT = BACKEND_ROOT / "uploads"
CHUNK_SIZE = 64 * 1024
IMAGE_LIMIT = 5 * 1024 * 1024
VIDEO_LIMIT = 30 * 1024 * 1024
TYPES = {
    ".png": ("image", "image/png", IMAGE_LIMIT),
    ".jpg": ("image", "image/jpeg", IMAGE_LIMIT),
    ".jpeg": ("image", "image/jpeg", IMAGE_LIMIT),
    ".mp4": ("video", "video/mp4", VIDEO_LIMIT),
}
logger = logging.getLogger(__name__)


def safe_directory(path: Path) -> Path:
    path = path.absolute()
    if path.is_symlink() or path.is_junction() or path.resolve() != path:
        raise OSError("Unsafe storage directory")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise OSError("Storage directory unavailable")
    return path


def file_metadata(filename: str | None):
    # Both Windows and POSIX path separators must be removed before display.
    name = (filename or "").replace("\\", "/").split("/")[-1]
    if not name or name in (".", "..") or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise HTTPException(422, "파일 이름을 확인해 주세요.")
    extension = Path(name).suffix.lower()
    if extension not in TYPES:
        raise HTTPException(415, "PNG·JPG(JPEG) 또는 MP4 파일만 등록할 수 있습니다.")
    return name, extension, TYPES[extension]


def verify_mp4(path: Path):
    """Bounded ISO-BMFF container check, not a codec/playability guarantee."""
    with path.open("rb") as source:
        end = path.stat().st_size
        budget = 10000

        def boxes(start, stop):
            nonlocal budget
            while start < stop:
                budget -= 1
                if budget < 0 or stop - start < 8:
                    raise ValueError("Invalid MP4 boxes")
                source.seek(start)
                size, kind = struct.unpack(">I4s", source.read(8))
                header = 8
                if size == 1:
                    if stop - start < 16:
                        raise ValueError("Invalid MP4 box")
                    size = struct.unpack(">Q", source.read(8))[0]
                    header = 16
                elif size == 0:
                    size = stop - start
                if size < header or start + size > stop:
                    raise ValueError("Invalid MP4 length")
                yield kind, start + header, start + size
                start += size

        top = list(boxes(0, end))
        ftyp = next((box for box in top if box[0] == b"ftyp"), None)
        if not ftyp or ftyp[2] - ftyp[1] < 8 or ftyp[2] - ftyp[1] > 1024:
            raise ValueError("Missing MP4 brand")
        source.seek(ftyp[1])
        brand_data = source.read(ftyp[2] - ftyp[1])
        brands = {brand_data[:4]} | {brand_data[i:i + 4] for i in range(8, len(brand_data), 4)}
        if not brands.intersection({b"isom", b"iso2", b"iso3", b"iso4", b"iso5", b"iso6", b"mp41", b"mp42", b"avc1", b"M4V ", b"dash"}):
            raise ValueError("Not an MP4 container")
        if not any(k == b"mdat" and stop > start for k, start, stop in top):
            raise ValueError("Missing media data")
        has_video = False
        for kind, start, stop in top:
            if kind != b"moov":
                continue
            for tk, ts, te in boxes(start, stop):
                if tk != b"trak":
                    continue
                for mk, ms, me in boxes(ts, te):
                    if mk != b"mdia":
                        continue
                    for hk, hs, he in boxes(ms, me):
                        if hk == b"hdlr" and he - hs >= 12:
                            source.seek(hs + 8)
                            if source.read(4) == b"vide":
                                has_video = True
        if not has_video:
            raise ValueError("Missing video track")


def verify_format(path: Path, extension: str):
    try:
        if extension == ".mp4":
            verify_mp4(path)
        else:
            expected = "PNG" if extension == ".png" else "JPEG"
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(path, formats=[expected]) as image:
                    image.verify()
                # Verify decoding, not just the magic bytes; never rewrite originals.
                with Image.open(path, formats=[expected]) as image:
                    image.load()
    except (UnidentifiedImageError, ValueError, SyntaxError, struct.error,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(415, "파일의 실제 형식을 확인할 수 없습니다. 올바른 이미지 또는 MP4 파일을 선택해 주세요.") from None
    except OSError:
        # Pillow reports malformed/truncated images using OSError as well.
        if extension != ".mp4":
            raise HTTPException(415, "손상되었거나 지원하지 않는 이미지입니다.") from None
        raise


def remove_owned(path: Path | None):
    if path is not None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.error("Material storage cleanup failed; storage reconciliation required")


def stage_file(upload, root: Path, owner_id: int):
    name, extension, (media_type, mime_type, limit) = file_metadata(upload.filename)
    root = safe_directory(root)
    temporary = safe_directory(root / ".tmp")
    owner_dir = safe_directory(root / str(owner_id))
    pending = None
    try:
        fd, raw_path = tempfile.mkstemp(prefix="upload-", dir=temporary)
        pending = Path(raw_path)
        size = 0
        with os.fdopen(fd, "wb") as target:
            while chunk := upload.file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, "이미지는 최대 5MiB, 영상은 최대 30MiB까지 등록할 수 있습니다.")
                target.write(chunk)
        if size == 0:
            raise HTTPException(422, "내용이 없는 파일은 등록할 수 없습니다.")
        verify_format(pending, extension)
        stored = uuid.uuid4().hex + (".jpg" if extension == ".jpeg" else extension)
        return pending, owner_dir / stored, dict(
            original_filename=name, stored_filename=stored, media_type=media_type,
            mime_type=mime_type, size_bytes=size,
        )
    except BaseException:
        remove_owned(pending)
        raise


def promote_file(pending: Path, final: Path):
    # Same filesystem, atomic exclusive creation: never replace an existing file.
    os.link(pending, final)


def material_path(root: Path, owner_id: int, stored_filename: str) -> Path:
    # Reading/deleting must never create missing directories or accept DB paths.
    if not re.fullmatch(r"[0-9a-f]{32}\.(png|jpg|jpeg|mp4)", stored_filename):
        raise OSError("Invalid stored name")
    root = root.absolute()
    parent = root / str(owner_id)
    for directory in (root, parent):
        if directory.is_symlink() or directory.is_junction() or directory.resolve() != directory:
            raise OSError("Unsafe storage directory")
    path = parent / stored_filename
    if path.is_symlink() or path.is_junction():
        raise OSError("Unsafe stored file")
    return path


def open_original(path: Path):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise OSError("Not a regular stored file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        current = os.fstat(fd)
        if not stat.S_ISREG(current.st_mode) or (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino):
            raise OSError("Stored file changed while opening")
        stream = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    return stream, current


def quarantine_file(path: Path, root: Path) -> Path | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise OSError("Not a regular stored file")
    trash = safe_directory(root.absolute() / ".trash")
    # Preserve the storage key in the internal trash name for manual recovery.
    quarantined = trash / (uuid.uuid4().hex + "-" + path.name)
    os.rename(path, quarantined)
    return quarantined


def restore_file(quarantined: Path, original: Path):
    # Exclusive link avoids overwriting a file unexpectedly created during recovery.
    os.link(quarantined, original)
    quarantined.unlink()
