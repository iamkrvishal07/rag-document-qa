import json
import time
from pathlib import Path

from app.core.config import settings
from app.core.redis import redis_client


CLEANUP_REGISTRY_KEY = "session_cleanup_registry"


async def register_session_cleanup(
    *,
    session_id: str,
    document_id: str,
) -> None:
    expires_at = (
        int(time.time())
        + settings.SESSION_EXPIRY_SECONDS
    )

    payload = {
        "session_id": session_id,
        "document_id": document_id,
    }

    await redis_client.zadd(
        CLEANUP_REGISTRY_KEY,
        {
            json.dumps(payload): expires_at,
        },
    )


async def refresh_session_cleanup(
    *,
    session_id: str,
    document_id: str,
) -> None:
    await register_session_cleanup(
        session_id=session_id,
        document_id=document_id,
    )


async def cleanup_expired_sessions() -> int:
    now = int(time.time())

    expired_entries = (
        await redis_client.zrangebyscore(
            CLEANUP_REGISTRY_KEY,
            min=0,
            max=now,
        )
    )

    cleaned_count = 0

    for raw_entry in expired_entries:
        try:
            entry = json.loads(
                raw_entry
            )

            session_id = entry[
                "session_id"
            ]

            document_id = entry[
                "document_id"
            ]

            # If session is still active,
            # its TTL was refreshed.
            if await redis_client.exists(
                f"session:{session_id}"
            ):
                ttl = await redis_client.ttl(
                    f"session:{session_id}"
                )

                if ttl > 0:
                    new_expiry = (
                        int(time.time())
                        + ttl
                    )

                    await redis_client.zadd(
                        CLEANUP_REGISTRY_KEY,
                        {
                            raw_entry:
                                new_expiry
                        },
                    )

                    continue

            upload_directory = (
                Path(settings.UPLOAD_DIR)
                / document_id
            )

            chroma_directory = (
                Path(settings.CHROMA_DIR)
                / document_id
            )

            if upload_directory.exists():
                import shutil

                shutil.rmtree(
                    upload_directory,
                    ignore_errors=True,
                )

            if chroma_directory.exists():
                import shutil

                shutil.rmtree(
                    chroma_directory,
                    ignore_errors=True,
                )

            await redis_client.delete(
                f"document:{document_id}",
                f"session:{session_id}",
                (
                    f"session:"
                    f"{session_id}:document"
                ),
                (
                    f"session:{session_id}:"
                    f"document:{document_id}:history"
                ),
            )

            await redis_client.zrem(
                CLEANUP_REGISTRY_KEY,
                raw_entry,
            )

            cleaned_count += 1

        except Exception as exc:
            print(
                "Session cleanup failed: "
                f"{exc}"
            )

    return cleaned_count
