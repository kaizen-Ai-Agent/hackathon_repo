from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from app.core.config import settings
import aioredis


class SchedulerService:
    def __init__(self):
        self.jobstores = None
        self.scheduler = None
        self.redis = None


    async def init_app(self):
        self.redis = await aioredis.from_url(settings.REDIS_URL)
        self.jobstores = {
        'default': RedisJobStore(redis_pool=self.redis, jobs_key='apscheduler.jobs', run_times_key='apscheduler.run_times')
        }
        self.scheduler = AsyncIOScheduler(jobstores=self.jobstores, timezone=settings.SCHEDULER_TIMEZONE)
        # Note: do NOT start scheduler in API containers when using split-process topology


    async def shutdown(self):
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
        if self.redis:
            await self.redis.close()


    # helpers used by API container to add/reschedule jobs
    def add_job(self, *args, **kwargs):
        return self.scheduler.add_job(*args, **kwargs)


    def reschedule_job(self, *args, **kwargs):
        return self.scheduler.reschedule_job(*args, **kwargs)


scheduler = SchedulerService()