from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from langchain_core.documents import (
    Document,
)

from app.services.retrieval_service import (
    retrieve_relevant_chunks,
)


def make_document(
    text: str,
    page: int = 1,
):
    return Document(
        page_content=text,
        metadata={
            "page": page,
        },
    )


async def retrieve(vector_store, *, mode="focused", question="question"):
    with patch(
        "app.services.retrieval_service.get_document_vector_store",
        return_value=vector_store,
    ):
        return await retrieve_relevant_chunks(
            document_id="test-doc",
            question=question,
            mode=mode,
        )


@pytest.mark.asyncio
async def test_focused_retrieval():
    vector_store = MagicMock()
    vector_store.similarity_search_with_relevance_scores.return_value = [
        (make_document("Relevant content"), 0.90),
        (make_document("Another relevant chunk", 2), 0.80),
    ]

    results = await retrieve(vector_store)

    assert len(results) == 2
    assert results[0][1] == 0.90


@pytest.mark.asyncio
async def test_focused_filters_low_scores():
    vector_store = MagicMock()
    vector_store.similarity_search_with_relevance_scores.return_value = [
        (make_document("High relevance"), 0.90),
        (make_document("Low relevance", 2), 0.20),
    ]

    results = await retrieve(vector_store)

    assert len(results) == 1
    assert results[0][1] == 0.90


@pytest.mark.asyncio
async def test_focused_fallback_threshold():
    vector_store = MagicMock()
    vector_store.similarity_search_with_relevance_scores.return_value = [
        (make_document("Fallback chunk"), 0.50),
        (make_document("Bad chunk", 2), 0.20),
    ]

    results = await retrieve(vector_store)

    assert len(results) == 1
    assert results[0][1] == 0.50


@pytest.mark.asyncio
async def test_tiny_document_safeguard():
    vector_store = MagicMock()
    vector_store.similarity_search_with_relevance_scores.return_value = [
        (make_document("Only document chunk"), 0.20),
    ]

    results = await retrieve(
        vector_store,
        question="what is this document about?",
    )

    assert len(results) == 1
    assert results[0][0].page_content == "Only document chunk"


@pytest.mark.asyncio
async def test_no_results():
    vector_store = MagicMock()
    vector_store.similarity_search_with_relevance_scores.return_value = []

    results = await retrieve(vector_store)

    assert results == []


@pytest.mark.asyncio
async def test_comparative_retrieval():
    vector_store = MagicMock()
    vector_store.similarity_search_with_relevance_scores.return_value = [
        (make_document("Project A"), 0.91),
        (make_document("Project B", 2), 0.88),
    ]

    results = await retrieve(
        vector_store,
        mode="comparative",
        question="compare project A and B",
    )

    assert len(results) == 2


@pytest.mark.asyncio
async def test_comparative_tiny_document():
    vector_store = MagicMock()
    vector_store.similarity_search_with_relevance_scores.return_value = [
        (make_document("Only chunk"), 0.10),
    ]

    results = await retrieve(
        vector_store,
        mode="comparative",
        question="compare content",
    )

    assert len(results) == 1


@pytest.mark.asyncio
async def test_broad_retrieval():
    vector_store = MagicMock()
    vector_store.max_marginal_relevance_search.return_value = [
        make_document("Topic A"),
        make_document("Topic B", 2),
        make_document("Topic C", 3),
    ]

    results = await retrieve(
        vector_store,
        mode="broad",
        question="summarize the document",
    )

    assert len(results) == 3

    for document, score in results:
        assert isinstance(document, Document)
        assert score == 1.0


@pytest.mark.asyncio
async def test_unknown_mode_uses_focused():
    vector_store = MagicMock()
    vector_store.similarity_search_with_relevance_scores.return_value = [
        (make_document("Content"), 0.90),
    ]

    results = await retrieve(
        vector_store,
        mode="unknown",
    )

    assert len(results) == 1
    vector_store.similarity_search_with_relevance_scores.assert_called_once()
