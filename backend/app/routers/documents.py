from pathlib import Path
import asyncio

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    UploadFile,
)
from fastapi.responses import (
    FileResponse,
    JSONResponse,
)

from app.core.config import settings
from app.services.document_processor import (
    create_document_preview,
    process_document,
)
from app.services.document_service import (
    create_session,
    delete_document_data,
    get_document_metadata,
    save_document,
    session_exists,
)
from app.utils.file_validation import (
    get_file_extension,
    is_file_readable,
    is_supported_file,
)


PROCESSING_PROGRESS = {
    "extracting_text": 20,
    "splitting_document": 40,
    "creating_embeddings": 60,
    "indexing_document": 80,
    "ready": 100,
    "failed": 100,
}

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
)


@router.post(
    "/upload",
    status_code=202,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
):
    filename = Path(file.filename or "").name

    # 1. Validate file type
    if not is_supported_file(
        filename,
        file.content_type,
    ):
        return JSONResponse(
            status_code=400,
            content={
                "error": "unsupported_file_type",
                "message": (
                    "Only PDF and DOCX files are supported."
                ),
            },
        )

    # 2. Read uploaded file
    file_bytes = await file.read()

    # 3. Validate file size
    max_size_bytes = (
        settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    )

    if len(file_bytes) > max_size_bytes:
        return JSONResponse(
            status_code=413,
            content={
                "error": "file_too_large",
                "message": "File exceeds the 5MB limit.",
                "max_size_bytes": max_size_bytes,
            },
        )

    # 4. Validate that file is actually readable
    extension = get_file_extension(filename)

    if not is_file_readable(
        file_bytes,
        extension,
    ):
        return JSONResponse(
            status_code=422,
            content={
                "error": "corrupted_file",
                "message": (
                    "The file could not be read. "
                    "It may be corrupted."
                ),
            },
        )

    # 5. Create session automatically when omitted
    if session_id is None:
        session = await create_session()
        session_id = session["session_id"]

    else:
        exists = await session_exists(
            session_id
        )

        if not exists:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "session_not_found",
                    "message": (
                        "The session does not exist "
                        "or has expired."
                    ),
                },
            )

    # 6. Store file + metadata
    metadata = await save_document(
        file_bytes=file_bytes,
        filename=filename,
        file_type=extension.lstrip("."),
        session_id=session_id,
    )

    background_tasks.add_task(
        process_document,
        metadata["document_id"],
    )

    # 7. Exact public response
    return {
        "document_id": metadata["document_id"],
        "session_id": metadata["session_id"],
        "filename": metadata["filename"],
        "file_type": metadata["file_type"],
        "file_size_bytes": metadata[
            "file_size_bytes"
        ],
        "status": metadata["status"],
        "status_detail": metadata[
            "status_detail"
        ],
    }


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
):
    metadata = await get_document_metadata(
        document_id
    )

    if metadata is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "document_not_found",
            },
        )

    status = metadata["status"]
    status_detail = metadata["status_detail"]

    if status == "processing":
        return {
            "document_id": document_id,
            "status": status,
            "status_detail": status_detail,
            "progress_percent": (
                PROCESSING_PROGRESS.get(
                    status_detail,
                    0,
                )
            ),
        }

    if status == "failed":
        error = metadata.get(
            "error",
            "document_processing_failed",
        )

        if error == "no_extractable_text":
            message = (
                "No text could be extracted from this "
                "document. If it is a scanned PDF, "
                "OCR may have failed."
            )
        else:
            message = (
                "The document could not be processed."
            )

        return {
            "document_id": document_id,
            "status": "failed",
            "status_detail": "failed",
            "error": error,
            "message": message,
        }

    return {
        "document_id": document_id,
        "status": "ready",
        "status_detail": "ready",
        "filename": metadata["filename"],
        "file_type": metadata["file_type"],
        "page_count": metadata.get(
            "page_count",
            0,
        ),
        "upload_time": metadata["upload_time"],
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str,
):
    metadata = await get_document_metadata(
        document_id
    )

    if metadata is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "document_not_found",
            },
        )

    return {
        "document_id": metadata[
            "document_id"
        ],
        "filename": metadata["filename"],
        "file_type": metadata["file_type"],
        "file_size_bytes": metadata[
            "file_size_bytes"
        ],
        "page_count": metadata.get(
            "page_count",
            0,
        ),
        "status": metadata["status"],
        "upload_time": metadata[
            "upload_time"
        ],
    }

@router.delete(
    "/{document_id}",
    status_code=204,
)
async def delete_document(
    document_id: str,
):
    deleted = await delete_document_data(
        document_id
    )

    if not deleted:
        return JSONResponse(
            status_code=404,
            content={
                "error": "document_not_found",
            },
        )

    return None



@router.get("/{document_id}/preview")
async def get_document_preview(
    document_id: str,
):
    metadata = await get_document_metadata(
        document_id
    )

    if metadata is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "document_not_found",
            },
        )

    if metadata["status"] != "ready":
        return JSONResponse(
            status_code=409,
            content={
                "error": "document_not_ready",
                "status": metadata["status"],
            },
        )

    preview = await asyncio.to_thread(
        create_document_preview,
        file_path=metadata["storage_path"],
        file_type=metadata["file_type"],
        document_id=document_id,
    )

    return preview


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str,
):
    metadata = await get_document_metadata(
        document_id
    )

    if metadata is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "document_not_found",
            },
        )

    file_path = Path(
        metadata["storage_path"]
    )

    if not file_path.exists():
        return JSONResponse(
            status_code=404,
            content={
                "error": "document_not_found",
            },
        )

    if metadata["file_type"] == "pdf":
        media_type = "application/pdf"

    else:
        media_type = (
            "application/"
            "vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=metadata["filename"],
    )
