import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.redis import redis_client


async def create_session() -> str:
    session_id = str(uuid.uuid4())

    session_data = {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await redis_client.set(
        f"session:{session_id}",
        json.dumps(session_data),
        ex=settings.SESSION_EXPIRY_SECONDS,
    )

    return session_id


async def session_exists(session_id: str) -> bool:
    return bool(
        await redis_client.exists(f"session:{session_id}")
    )


async def save_document(
    *,
    file_bytes: bytes,
    filename: str,
    file_type: str,
    session_id: str,
) -> dict:
    document_id = str(uuid.uuid4())

    upload_directory = (
        Path(settings.UPLOAD_DIR) / document_id
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    storage_path = upload_directory / filename

    try:
        storage_path.write_bytes(file_bytes)

        document_metadata = {
            "document_id": document_id,
            "session_id": session_id,
            "filename": filename,
            "file_type": file_type,
            "file_size_bytes": len(file_bytes),
            "upload_time": datetime.now(
                timezone.utc
            ).isoformat(),
            "status": "processing",
            "status_detail": "extracting_text",
            "storage_path": str(storage_path),
        }

        await redis_client.set(
            f"document:{document_id}",
            json.dumps(document_metadata),
            ex=settings.SESSION_EXPIRY_SECONDS,
        )

        await redis_client.set(
            f"session:{session_id}:document",
            document_id,
            ex=settings.SESSION_EXPIRY_SECONDS,
        )

        # Refresh session TTL because this is activity.
        await redis_client.expire(
            f"session:{session_id}",
            settings.SESSION_EXPIRY_SECONDS,
        )

        return document_metadata

    except Exception:
        if upload_directory.exists():
            shutil.rmtree(
                upload_directory,
                ignore_errors=True,
            )

        raise