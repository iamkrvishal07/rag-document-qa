import pytest

from app.services.llm_service import (
    _parse_retrieval_plan,
)


def test_parse_valid_json():
    content = (
        '{"mode": "focused", '
        '"query": "cat green eyes"}'
    )

    result = _parse_retrieval_plan(
        content,
        "original question",
    )

    assert result == {
        "mode": "focused",
        "query": "cat green eyes",
    }


def test_parse_fenced_json():
    content = """
```json
{
    "mode": "broad",
    "query": "main ideas"
}
```
"""

    result = _parse_retrieval_plan(
        content,
        "summarize document",
    )

    assert result == {
        "mode": "broad",
        "query": "main ideas",
    }


def test_parse_python_style_dict():
    content = (
        "{'mode': 'comparative', "
        "'query': 'compare projects'}"
    )

    result = _parse_retrieval_plan(
        content,
        "compare them",
    )

    assert result == {
        "mode": "comparative",
        "query": "compare projects",
    }


def test_parse_json_with_extra_text():
    content = """
Here is the retrieval plan:

{
    "mode": "focused",
    "query": "cat description"
}
"""

    result = _parse_retrieval_plan(
        content,
        "tell me about cat",
    )

    assert result["mode"] == "focused"
    assert result["query"] == "cat description"


def test_invalid_mode_defaults_to_focused():
    content = (
        '{"mode": "random", '
        '"query": "hello"}'
    )

    result = _parse_retrieval_plan(
        content,
        "hello",
    )

    assert result["mode"] == "focused"


def test_empty_query_uses_original_question():
    content = (
        '{"mode": "focused", '
        '"query": ""}'
    )

    result = _parse_retrieval_plan(
        content,
        "original question",
    )

    assert result["query"] == "original question"


def test_invalid_content_raises_error():
    with pytest.raises(ValueError):
        _parse_retrieval_plan(
            "not json at all",
            "question",
        )
