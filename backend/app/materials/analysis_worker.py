import asyncio

from app.materials.analysis_client import OpenAISummarizer
from app.materials.analysis_media import prepare, reconcile_temp
from app.materials.analysis_repository import claim, configured, finish, still_current
from app.materials.analysis_schemas import AnalysisFailure
from app.materials.storage import logger


class AnalysisWorker:
    def __init__(self, engine, settings, root, adapter=None):
        self.engine, self.settings, self.root = engine, settings, root
        self.adapter = adapter
        self.event = asyncio.Event()
        self.stopping = False
        self.task = None

    def start(self):
        if configured(self.settings):
            if self.adapter is None:
                self.adapter = OpenAISummarizer(self.settings)
            self.task = asyncio.create_task(self.run(), name='materials-analysis')

    def wake(self):
        self.event.set()

    async def stop(self):
        self.stopping = True
        self.wake()
        if self.task:
            try:
                await asyncio.wait_for(asyncio.shield(self.task), timeout=10)
            except TimeoutError:
                self.task.cancel()
                await asyncio.gather(self.task, return_exceptions=True)
        if self.adapter:
            await self.adapter.close()

    async def run(self):
        try:
            await asyncio.to_thread(reconcile_temp, self.engine, self.root)
        except Exception:
            logger.warning('Analysis temporary-file reconciliation deferred; check database/storage')
        while not self.stopping:
            self.event.clear()
            try:
                job = await asyncio.to_thread(claim, self.engine, self.settings)
                if job:
                    await self.process(job)
                    continue
            except Exception:
                # Deliberately exclude raw database/provider exception text.
                logger.warning('Analysis queue unavailable; check migrations and database connectivity')
            try:
                await asyncio.wait_for(self.event.wait(), timeout=self.settings.analysis_poll_seconds)
            except TimeoutError:
                pass

    async def process(self, job):
        result, code = None, None
        try:
            async with asyncio.timeout(self.settings.analysis_job_seconds):
                prepared = await prepare(self.root, job)
                if not await asyncio.to_thread(still_current, self.engine, job):
                    return
                result = await self.adapter.summarize(job, prepared)
        except asyncio.CancelledError:
            await asyncio.to_thread(finish, self.engine, job, code='interrupted')
            raise
        except TimeoutError:
            code = 'timeout'
        except AnalysisFailure as error:
            code = error.code
        except Exception:
            code = 'internal_error'
        await asyncio.to_thread(finish, self.engine, job, code=code, result=result,
                                model=self.settings.openai_model)
