import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.config import settings
from db.prisma_client import prisma
from services.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await prisma.connect()
    await scheduler.init_app()
    yield
    
    # shutdown
    await scheduler.shutdown()
    await prisma.disconnect()

app = FastAPI(lifespan=lifespan)

# include routers
from api.router import router as api_router
app.include_router(api_router, prefix="/api/v1")

@app.get('/health')
async def health():
    return {"status": "ok"}