import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.redis import redis_client

from app.routers.documents import (
    router as documents_router,
)

from app.routers.chat import (
    router as chat_router,
)

from app.routers.session import (
    router as session_router,
)

from app.services.session_cleanup_service import (
    cleanup_expired_sessions,
)


async def cleanup_loop():
    while True:
        try:
            cleaned = await cleanup_expired_sessions()

            if cleaned > 0:
                print(
                    f"Cleaned {cleaned} "
                    "expired session(s)."
                )

        except Exception as exc:
            print(
                "Cleanup job error: "
                f"{exc}"
            )

        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.ping()

    cleanup_task = asyncio.create_task(
        cleanup_loop()
    )

    try:
        yield

    finally:
        cleanup_task.cancel()

        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

        await redis_client.aclose()


app = FastAPI(
    title="RAG Document Q&A API",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(session_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok"
    }


@app.get("/health/redis")
async def redis_health_check():
    await redis_client.ping()

    return {
        "status": "ok",
        "redis": "connected",
    }
