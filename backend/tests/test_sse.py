import json

from app.utils.sse import sse_event


def test_sse_event_format():
    result = sse_event(
        "token",
        {
            "token": "Hello",
        },
    )

    assert result.startswith(
        "event: token\n"
    )
    assert "data: " in result
    assert result.endswith(
        "\n\n"
    )


def test_sse_event_json_payload():
    result = sse_event(
        "done",
        {
            "success": True,
        },
    )

    data_line = result.split(
        "data: ",
        1,
    )[1].strip()

    payload = json.loads(
        data_line
    )

    assert payload == {
        "success": True,
    }


def test_sse_event_unicode():
    result = sse_event(
        "token",
        {
            "token": "नमस्ते",
        },
    )

    assert "नमस्ते" in result
