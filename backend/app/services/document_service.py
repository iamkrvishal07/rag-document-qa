import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.redis import redis_client


from app.services.session_cleanup_service import (
    CLEANUP_REGISTRY_KEY,
    register_session_cleanup,
)

async def create_session() -> dict:
    session_id = str(uuid.uuid4())

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    session_data = {
        "session_id": session_id,
        "created_at": created_at,
    }

    await redis_client.set(
        f"session:{session_id}",
        json.dumps(session_data),
        ex=settings.SESSION_EXPIRY_SECONDS,
    )

    return {
        "session_id": session_id,
        "created_at": created_at,
        "expires_in_seconds": (
            settings.SESSION_EXPIRY_SECONDS
        ),
    }


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

        # await redis_client.set(
        #     f"session:{session_id}:document",
        #     document_id,
        #     ex=settings.SESSION_EXPIRY_SECONDS,
        # )

        # # Refresh session TTL because this is activity.
        # await redis_client.expire(
        #     f"session:{session_id}",
        #     settings.SESSION_EXPIRY_SECONDS,
        # )

        await redis_client.set(
            f"session:{session_id}:document",
            document_id,
            ex=settings.SESSION_EXPIRY_SECONDS,
        )

        await register_session_cleanup(
            session_id=session_id,
            document_id=document_id,
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

async def get_document_metadata(
    document_id: str,
) -> dict | None:
    raw_metadata = await redis_client.get(
        f"document:{document_id}"
    )

    if raw_metadata is None:
        return None

    return json.loads(raw_metadata)

async def delete_document_data(
    document_id: str,
) -> bool:
    metadata = await get_document_metadata(
        document_id
    )

    if metadata is None:
        return False

    session_id = metadata["session_id"]

    # Delete original upload
    storage_path = Path(
        metadata["storage_path"]
    )

    upload_directory = storage_path.parent

    if upload_directory.exists():
        shutil.rmtree(
            upload_directory,
            ignore_errors=True,
        )

    # Delete Chroma persistence
    chroma_directory = (
        Path(settings.CHROMA_DIR)
        / document_id
    )

    if chroma_directory.exists():
        shutil.rmtree(
            chroma_directory,
            ignore_errors=True,
        )

    # Delete Redis document metadata and chat history
    await redis_client.delete(
        f"document:{document_id}",
        (
            f"session:{session_id}:"
            f"document:{document_id}:history"
        ),
    )

    # Remove active-document pointer only if
    # it still points to this document
    session_document_key = (
        f"session:{session_id}:document"
    )

    active_document_id = (
        await redis_client.get(
            session_document_key
        )
    )

    if active_document_id == document_id:
        await redis_client.delete(
            session_document_key
        )

    cleanup_payload = {
        "session_id": session_id,
        "document_id": document_id,
    }

    await redis_client.zrem(
        CLEANUP_REGISTRY_KEY,
        json.dumps(cleanup_payload),
    )

    return True
