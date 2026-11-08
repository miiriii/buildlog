"""Decode untrusted media in a time/memory bounded, disposable child process."""
import asyncio
import base64
import json
import math
import multiprocessing
from pathlib import Path
import time
from uuid import UUID

import psutil

from app.materials import storage
from app.materials.analysis_schemas import AnalysisFailure

MAX_PIXELS = 40_000_000
MAX_OUTPUT = 4 * 1024 * 1024
PREPROCESS_SECONDS = 15
RSS_LIMIT = 512 * 1024 * 1024


def _decode(source, directory, kind):
    # Imports in the child keep codec state out of the web server process.
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    directory = Path(directory)
    frames, timestamps = [], []

    def save(image, index, limit):
        if image.width * image.height > MAX_PIXELS:
            raise AnalysisFailure('preprocessing_limit')
        image = ImageOps.exif_transpose(image)
        if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
            rgba = image.convert('RGBA')
            background = Image.new('RGBA', rgba.size, 'white')
            image = Image.alpha_composite(background, rgba)
        image = image.convert('RGB')
        image.thumbnail((limit, limit))
        path = directory / f'frame-{index}.jpg'
        image.save(path, 'JPEG', quality=80, optimize=True)
        frames.append(path.name)
        if sum((directory / name).stat().st_size for name in frames) > MAX_OUTPUT:
            raise AnalysisFailure('preprocessing_limit')

    try:
        if kind == 'image':
            with Image.open(source) as image:
                save(image, 0, 1536)
        else:
            import av
            with av.open(source) as container:
                stream = next((s for s in container.streams.video), None)
                if stream is None or not stream.duration or not stream.time_base:
                    raise AnalysisFailure('unsupported_video')
                if stream.width * stream.height > MAX_PIXELS:
                    raise AnalysisFailure('preprocessing_limit')
                duration = float(stream.duration * stream.time_base)
                if not math.isfinite(duration) or duration <= 0:
                    raise AnalysisFailure('unsupported_video')
                count = min(8, max(1, math.ceil(duration / 5)))
                for index in range(count):
                    timestamp = duration * (index + .5) / count
                    container.seek(int(timestamp / stream.time_base), stream=stream, backward=True)
                    frame = None
                    for candidate in container.decode(stream):
                        frame = candidate
                        if candidate.time is not None and candidate.time >= timestamp:
                            break
                    if frame is None:
                        raise AnalysisFailure('unsupported_video')
                    save(frame.to_image(), index, 1024)
                    timestamps.append(round(float(frame.time or timestamp), 3))
        payload = {'frames': frames, 'scope': {'kind': kind if kind == 'image' else 'video_frames',
            'frame_count': len(frames), 'timestamps': timestamps, 'audio_included': False}}
    except AnalysisFailure as error:
        payload = {'error': error.code}
    except Exception:
        payload = {'error': 'invalid_media' if kind == 'image' else 'unsupported_video'}
    (directory / 'result.json').write_text(json.dumps(payload), encoding='utf-8')


def cleanup(directory):
    # Only files in our UUID work directory; never recurse through user paths.
    if directory is None:
        return
    try:
        for path in directory.iterdir():
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)
        directory.rmdir()
    except OSError:
        storage.logger.warning('Analysis temporary-file cleanup requires reconciliation')


def reconcile_temp(engine, root):
    from datetime import UTC, datetime
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.materials.models import Material
    parent = Path(root) / '.analysis'
    if not parent.exists():
        return
    parent = storage.safe_directory(parent)
    directories = list(parent.iterdir())
    with Session(engine) as session:
        active = set(session.scalars(select(Material.analysis_job_token).where(
            Material.analysis_status == 'processing', Material.analysis_lease_expires_at > datetime.now(UTC))))
    for directory in directories:
        try:
            valid = str(UUID(directory.name)) == directory.name
        except ValueError:
            continue
        if valid and directory.name not in active and directory.is_dir() and not directory.is_symlink() and not directory.is_junction():
            cleanup(directory)


async def prepare(root, job):
    directory = None
    process = None
    try:
        parent = storage.safe_directory(Path(root) / '.analysis')
        directory = storage.safe_directory(parent / job['token'])
        original = storage.material_path(root, job['owner_id'], job['stored_filename'])
        stream, _info = storage.open_original(original)
        source = directory / 'source'
        with stream, source.open('xb') as target:
            total = 0
            while data := stream.read(64 * 1024):
                total += len(data)
                if total > 30 * 1024 * 1024:
                    raise AnalysisFailure('preprocessing_limit')
                target.write(data)
        process = multiprocessing.get_context('spawn').Process(
            target=_decode, args=(str(source), str(directory), job['media_type']), daemon=True)
        process.start()
        deadline = time.monotonic() + PREPROCESS_SECONDS
        monitor = psutil.Process(process.pid)
        while process.is_alive():
            if time.monotonic() > deadline:
                raise AnalysisFailure('preprocessing_limit')
            try:
                if monitor.memory_info().rss > RSS_LIMIT:
                    raise AnalysisFailure('preprocessing_limit')
            except psutil.NoSuchProcess:
                break
            await asyncio.sleep(.05)
        process.join(timeout=1)
        result_path = directory / 'result.json'
        if process.exitcode != 0 or not result_path.exists() or result_path.stat().st_size > 8192:
            raise AnalysisFailure('invalid_media' if job['media_type'] == 'image' else 'unsupported_video')
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if result.get('error'):
            raise AnalysisFailure(result['error'])
        images = []
        total = 0
        for index, name in enumerate(result['frames']):
            if name != f'frame-{index}.jpg' or index >= 8:
                raise AnalysisFailure('invalid_media')
            content = (directory / name).read_bytes()
            total += len(content)
            if total > MAX_OUTPUT:
                raise AnalysisFailure('preprocessing_limit')
            images.append('data:image/jpeg;base64,' + base64.b64encode(content).decode('ascii'))
        return {'images': images, 'scope': result['scope']}
    except FileNotFoundError:
        raise AnalysisFailure('original_missing') from None
    except OSError:
        raise AnalysisFailure('invalid_media') from None
    finally:
        if process is not None and process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            process.close()
        cleanup(directory)
