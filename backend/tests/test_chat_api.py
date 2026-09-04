from unittest.mock import AsyncMock, patch

import pytest


def ask_payload(session_id="session-123", question="What is this?"):
    return {"session_id": session_id, "question": question}


@pytest.mark.asyncio
async def test_ask_document_not_found(client):
    with patch(
        "app.routers.chat.get_document_metadata",
        new=AsyncMock(return_value=None),
    ):
        response = await client.post(
            "/api/chat/missing-doc/ask", json=ask_payload()
        )
    assert response.status_code == 404
    assert response.json()["error"] == "document_not_found"


@pytest.mark.asyncio
async def test_ask_document_not_ready(client):
    metadata = {"status": "processing", "session_id": "session-123"}
    with patch(
        "app.routers.chat.get_document_metadata",
        new=AsyncMock(return_value=metadata),
    ):
        response = await client.post(
            "/api/chat/doc-123/ask", json=ask_payload(question="Summarize this")
        )
    assert response.status_code == 409
    assert response.json()["error"] == "document_not_ready"


@pytest.mark.asyncio
async def test_ask_wrong_session(client):
    metadata = {"status": "ready", "session_id": "owner-session"}
    with patch(
        "app.routers.chat.get_document_metadata",
        new=AsyncMock(return_value=metadata),
    ):
        response = await client.post(
            "/api/chat/doc-123/ask", json=ask_payload("wrong-session")
        )
    assert response.status_code == 404
    assert response.json()["error"] == "session_not_found"


@pytest.mark.asyncio
async def test_ask_expired_session(client):
    metadata = {"status": "ready", "session_id": "session-123"}
    with (
        patch(
            "app.routers.chat.get_document_metadata",
            new=AsyncMock(return_value=metadata),
        ),
        patch(
            "app.routers.chat.session_exists",
            new=AsyncMock(return_value=False),
        ),
    ):
        response = await client.post(
            "/api/chat/doc-123/ask", json=ask_payload()
        )
    assert response.status_code == 404
    assert response.json()["error"] == "session_not_found"


@pytest.mark.asyncio
async def test_ask_retrieval_failure(client):
    metadata = {"status": "ready", "session_id": "session-123"}
    with (
        patch("app.routers.chat.get_document_metadata", new=AsyncMock(return_value=metadata)),
        patch("app.routers.chat.session_exists", new=AsyncMock(return_value=True)),
        patch("app.routers.chat.get_chat_history", new=AsyncMock(return_value=[])),
        patch(
            "app.routers.chat.plan_retrieval_query",
            new=AsyncMock(return_value={"mode": "focused", "query": "test query"}),
        ),
        patch(
            "app.routers.chat.retrieve_relevant_chunks",
            new=AsyncMock(side_effect=Exception("Vector store unavailable")),
        ),
    ):
        response = await client.post(
            "/api/chat/doc-123/ask", json=ask_payload(question="Question")
        )
    assert response.status_code == 503
    assert response.json()["error"] == "index_unavailable"


@pytest.mark.asyncio
async def test_ask_no_results_stream(client):
    metadata = {"status": "ready", "session_id": "session-123"}
    with (
        patch("app.routers.chat.get_document_metadata", new=AsyncMock(return_value=metadata)),
        patch("app.routers.chat.session_exists", new=AsyncMock(return_value=True)),
        patch("app.routers.chat.get_chat_history", new=AsyncMock(return_value=[])),
        patch(
            "app.routers.chat.plan_retrieval_query",
            new=AsyncMock(return_value={"mode": "focused", "query": "unknown topic"}),
        ),
        patch("app.routers.chat.retrieve_relevant_chunks", new=AsyncMock(return_value=[])),
        patch("app.routers.chat.save_chat_exchange", new=AsyncMock()),
    ):
        response = await client.post(
            "/api/chat/doc-123/ask",
            json=ask_payload(question="Unknown question"),
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    for event in ("start", "token", "sources", "done"):
        assert f"event: {event}" in response.text
    assert "This information is not available" in response.text


@pytest.mark.asyncio
async def test_history_session_not_found(client):
    with patch("app.routers.chat.session_exists", new=AsyncMock(return_value=False)):
        response = await client.get("/api/chat/session-x/doc-123/history")
    assert response.status_code == 404
    assert response.json()["error"] == "session_not_found"


@pytest.mark.asyncio
async def test_get_chat_history(client):
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi", "sources": []},
    ]
    with (
        patch("app.routers.chat.session_exists", new=AsyncMock(return_value=True)),
        patch("app.routers.chat.get_chat_history", new=AsyncMock(return_value=messages)),
        patch("app.routers.chat.redis_client.expire", new=AsyncMock(return_value=True)),
        patch("app.routers.chat.refresh_session_cleanup", new=AsyncMock()),
    ):
        response = await client.get("/api/chat/session-123/doc-123/history")

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "session-123",
        "document_id": "doc-123",
        "messages": messages,
    }


@pytest.mark.asyncio
async def test_reset_chat_history(client):
    with (
        patch("app.routers.chat.session_exists", new=AsyncMock(return_value=True)),
        patch("app.routers.chat.clear_chat_history", new=AsyncMock()) as clear_mock,
        patch("app.routers.chat.redis_client.expire", new=AsyncMock(return_value=True)),
        patch("app.routers.chat.refresh_session_cleanup", new=AsyncMock()),
    ):
        response = await client.post("/api/chat/session-123/doc-123/reset")
    assert response.status_code == 204
    clear_mock.assert_awaited_once_with("session-123", "doc-123")


@pytest.mark.asyncio
async def test_reset_invalid_session(client):
    with patch("app.routers.chat.session_exists", new=AsyncMock(return_value=False)):
        response = await client.post("/api/chat/bad-session/doc-123/reset")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_invalid_format(client):
    with patch("app.routers.chat.session_exists", new=AsyncMock(return_value=True)):
        response = await client.get(
            "/api/chat/session-123/doc-123/export?format=pdf"
        )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_export_format"


@pytest.mark.asyncio
async def test_export_json(client):
    messages = [
        {"role": "user", "content": "What is RAG?"},
        {"role": "assistant", "content": "RAG combines retrieval and generation.", "sources": []},
    ]
    with (
        patch("app.routers.chat.session_exists", new=AsyncMock(return_value=True)),
        patch("app.routers.chat.get_chat_history", new=AsyncMock(return_value=messages)),
    ):
        response = await client.get(
            "/api/chat/session-123/doc-123/export?format=json"
        )

    assert response.status_code == 200
    assert response.json()["messages"] == messages
    assert "conversation.json" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_txt(client):
    messages = [
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": "Hi there",
            "sources": [{"type": "page", "number": 2}],
        },
    ]
    with (
        patch("app.routers.chat.session_exists", new=AsyncMock(return_value=True)),
        patch("app.routers.chat.get_chat_history", new=AsyncMock(return_value=messages)),
    ):
        response = await client.get(
            "/api/chat/session-123/doc-123/export?format=txt"
        )

    assert response.status_code == 200
    assert "User: Hello" in response.text
    assert "Assistant: Hi there" in response.text
    assert "Sources: Page 2" in response.text
    assert "conversation.txt" in response.headers["content-disposition"]
