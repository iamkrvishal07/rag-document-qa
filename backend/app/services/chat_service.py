import json
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.redis import redis_client


from app.services.session_cleanup_service import (
    refresh_session_cleanup,
)

def generate_message_id() -> str:
    return f"m_{uuid.uuid4().hex[:8]}"



async def save_chat_exchange(
    *,
    session_id: str,
    document_id: str,
    question: str,
    answer: str,
    sources: list[dict],
    assistant_message_id: str,
) -> tuple[dict, dict]:
    history_key = (
        f"session:{session_id}:"
        f"document:{document_id}:history"
    )

    user_message = {
        "message_id": generate_message_id(),
        "role": "user",
        "content": question,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    assistant_message = {
        "message_id": assistant_message_id,
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    pipeline = redis_client.pipeline(
        transaction=True
    )

    pipeline.rpush(
        history_key,
        json.dumps(user_message),
        json.dumps(assistant_message),
    )

    pipeline.expire(
        history_key,
        settings.SESSION_EXPIRY_SECONDS,
    )

    pipeline.expire(
        f"session:{session_id}",
        settings.SESSION_EXPIRY_SECONDS,
    )

    pipeline.expire(
        f"document:{document_id}",
        settings.SESSION_EXPIRY_SECONDS,
    )

    pipeline.expire(
        f"session:{session_id}:document",
        settings.SESSION_EXPIRY_SECONDS,
    )

    await pipeline.execute()
    
    await refresh_session_cleanup(
    session_id=session_id,
    document_id=document_id,
)

    return (
        user_message,
        assistant_message,
    )


async def get_chat_history(
    session_id: str,
    document_id: str,
) -> list[dict]:
    history_key = (
        f"session:{session_id}:"
        f"document:{document_id}:history"
    )

    raw_messages = await redis_client.lrange(
        history_key,
        0,
        -1,
    )

    return [
        json.loads(message)
        for message in raw_messages
    ]


async def clear_chat_history(
    session_id: str,
    document_id: str,
) -> None:
    await redis_client.delete(
        f"session:{session_id}:"
        f"document:{document_id}:history"
    )
