import pytest


@pytest.mark.asyncio
async def test_create_session(client):
    response = await client.post(
        "/session"
    )

    assert response.status_code == 201

    data = response.json()

    assert "session_id" in data
    assert isinstance(
        data["session_id"],
        str,
    )
    assert data["session_id"]
