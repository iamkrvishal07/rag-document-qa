import asyncio

from langchain_core.documents import Document

from app.core.config import settings
from app.services.embedding_service import (
    get_document_vector_store,
)


FOCUSED_CANDIDATE_K = 10

COMPARATIVE_CANDIDATE_K = 15
COMPARATIVE_FINAL_K = 8

BROAD_FINAL_K = 10
BROAD_FETCH_K = 30

FALLBACK_THRESHOLD = 0.45
FALLBACK_TOP_K = 3


async def retrieve_relevant_chunks(
    *,
    document_id: str,
    question: str,
    mode: str = "focused",
) -> list[tuple[Document, float]]:
    vector_store = (
        get_document_vector_store(
            document_id
        )
    )

    if mode == "broad":
        return await _retrieve_broad(
            vector_store=vector_store,
            question=question,
        )

    if mode == "comparative":
        return await _retrieve_comparative(
            vector_store=vector_store,
            question=question,
        )

    return await _retrieve_focused(
        vector_store=vector_store,
        question=question,
    )


async def _retrieve_focused(
    *,
    vector_store,
    question: str,
) -> list[tuple[Document, float]]:
    results = await asyncio.to_thread(
        vector_store.similarity_search_with_relevance_scores,
        question,
        k=FOCUSED_CANDIDATE_K,
    )

    if not results:
        return []

    # Tiny-document safeguard.
    #
    # If the complete indexed document is represented by
    # only one chunk, rejecting it solely because of a
    # similarity threshold can incorrectly discard the
    # entire document for broad/vague wording.
    if len(results) == 1:
        return results

    relevant_results = [
        (document, score)
        for document, score in results
        if score
        >= settings.SIMILARITY_THRESHOLD
    ]

    if relevant_results:
        return relevant_results[
            :settings.RETRIEVAL_TOP_K
        ]

    # Controlled generic fallback.
    fallback_results = [
        (document, score)
        for document, score in results
        if score >= FALLBACK_THRESHOLD
    ]

    return fallback_results[
        :FALLBACK_TOP_K
    ]


async def _retrieve_comparative(
    *,
    vector_store,
    question: str,
) -> list[tuple[Document, float]]:
    results = await asyncio.to_thread(
        vector_store.similarity_search_with_relevance_scores,
        question,
        k=COMPARATIVE_CANDIDATE_K,
    )

    if not results:
        return []

    # Same safeguard for very small documents.
    if len(results) == 1:
        return results

    relevant_results = [
        (document, score)
        for document, score in results
        if score
        >= settings.SIMILARITY_THRESHOLD
    ]

    if relevant_results:
        return relevant_results[
            :COMPARATIVE_FINAL_K
        ]

    fallback_results = [
        (document, score)
        for document, score in results
        if score >= FALLBACK_THRESHOLD
    ]

    return fallback_results[
        :COMPARATIVE_FINAL_K
    ]


async def _retrieve_broad(
    *,
    vector_store,
    question: str,
) -> list[tuple[Document, float]]:
    documents = await asyncio.to_thread(
        vector_store.max_marginal_relevance_search,
        question,
        k=BROAD_FINAL_K,
        fetch_k=BROAD_FETCH_K,
        lambda_mult=0.6,
    )

    # MMR returns Documents rather than relevance-score
    # tuples. The score is only a compatibility placeholder
    # for the current downstream pipeline and is never shown
    # to the user.
    return [
        (document, 1.0)
        for document in documents
    ]
