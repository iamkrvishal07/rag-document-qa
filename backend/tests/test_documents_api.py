from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_document_status_not_found(client):
    with patch(
        "app.routers.documents.get_document_metadata",
        new=AsyncMock(return_value=None),
    ):
        response = await client.get("/api/documents/missing-doc/status")

    assert response.status_code == 404
    assert response.json() == {"error": "document_not_found"}


@pytest.mark.asyncio
async def test_document_status_processing(client):
    metadata = {
        "status": "processing",
        "status_detail": "creating_embeddings",
    }
    with patch(
        "app.routers.documents.get_document_metadata",
        new=AsyncMock(return_value=metadata),
    ):
        response = await client.get("/api/documents/doc-123/status")

    assert response.status_code == 200
    assert response.json() == {
        "document_id": "doc-123",
        "status": "processing",
        "status_detail": "creating_embeddings",
        "progress_percent": 60,
    }


@pytest.mark.asyncio
async def test_document_status_ready(client):
    metadata = {
        "status": "ready",
        "status_detail": "ready",
        "filename": "sample.pdf",
        "file_type": "pdf",
        "page_count": 3,
        "upload_time": "2026-09-04T10:00:00+00:00",
    }
    with patch(
        "app.routers.documents.get_document_metadata",
        new=AsyncMock(return_value=metadata),
    ):
        response = await client.get("/api/documents/doc-123/status")

    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "ready"
    assert data["filename"] == "sample.pdf"
    assert data["file_type"] == "pdf"
    assert data["page_count"] == 3


@pytest.mark.asyncio
async def test_document_status_failed(client):
    metadata = {
        "status": "failed",
        "status_detail": "failed",
        "error": "no_extractable_text",
    }
    with patch(
        "app.routers.documents.get_document_metadata",
        new=AsyncMock(return_value=metadata),
    ):
        response = await client.get("/api/documents/doc-123/status")

    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "failed"
    assert data["error"] == "no_extractable_text"
    assert "No text could be extracted" in data["message"]


@pytest.mark.asyncio
async def test_get_document(client):
    metadata = {
        "document_id": "doc-123",
        "filename": "sample.pdf",
        "file_type": "pdf",
        "file_size_bytes": 1024,
        "page_count": 2,
        "status": "ready",
        "upload_time": "2026-09-04T10:00:00+00:00",
    }
    with patch(
        "app.routers.documents.get_document_metadata",
        new=AsyncMock(return_value=metadata),
    ):
        response = await client.get("/api/documents/doc-123")

    assert response.status_code == 200
    assert response.json() == metadata


@pytest.mark.asyncio
async def test_get_document_not_found(client):
    with patch(
        "app.routers.documents.get_document_metadata",
        new=AsyncMock(return_value=None),
    ):
        response = await client.get("/api/documents/missing-doc")

    assert response.status_code == 404
    assert response.json() == {"error": "document_not_found"}


@pytest.mark.asyncio
async def test_delete_document(client):
    with patch(
        "app.routers.documents.delete_document_data",
        new=AsyncMock(return_value=True),
    ):
        response = await client.delete("/api/documents/doc-123")

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_delete_document_not_found(client):
    with patch(
        "app.routers.documents.delete_document_data",
        new=AsyncMock(return_value=False),
    ):
        response = await client.delete("/api/documents/missing-doc")

    assert response.status_code == 404
    assert response.json() == {"error": "document_not_found"}


@pytest.mark.asyncio
async def test_preview_document_not_found(client):
    with patch(
        "app.routers.documents.get_document_metadata",
        new=AsyncMock(return_value=None),
    ):
        response = await client.get("/api/documents/missing-doc/preview")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_document_not_ready(client):
    with patch(
        "app.routers.documents.get_document_metadata",
        new=AsyncMock(return_value={"status": "processing"}),
    ):
        response = await client.get("/api/documents/doc-123/preview")

    assert response.status_code == 409
    assert response.json() == {
        "error": "document_not_ready",
        "status": "processing",
    }


@pytest.mark.asyncio
async def test_upload_unsupported_file(client):
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_file_type"


@pytest.mark.asyncio
async def test_upload_corrupted_pdf(client):
    response = await client.post(
        "/api/documents/upload",
        files={
            "file": (
                "broken.pdf",
                b"this is not a real pdf",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "corrupted_file"


@pytest.mark.asyncio
async def test_upload_invalid_session(client):
    with (
        patch("app.routers.documents.is_file_readable", return_value=True),
        patch(
            "app.routers.documents.session_exists",
            new=AsyncMock(return_value=False),
        ),
    ):
        response = await client.post(
            "/api/documents/upload",
            data={"session_id": "expired-session"},
            files={
                "file": (
                    "sample.pdf",
                    b"%PDF-1.4 fake",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 404
    assert response.json()["error"] == "session_not_found"
