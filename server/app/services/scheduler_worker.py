import asyncio
from app.services.scheduler import SchedulerService
from app.services.wrapup_job import meeting_wrapup_task


async def main_worker():
    sched = SchedulerService()
    await sched.init_app()
    # start scheduler to execute jobs
    sched.scheduler.start()
    # keep alive
    try:
        while True:
            await asyncio.sleep(60)
    finally:
        await sched.shutdown()


if __name__ == '__main__':
    asyncio.run(main_worker())