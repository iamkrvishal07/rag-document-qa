import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
)
from app.core.config import settings

from app.services.session_cleanup_service import (
    refresh_session_cleanup,
)

from fastapi import Response

from app.models.chat import (
    AskQuestionRequest,
)

from fastapi import Query
from fastapi.responses import Response

from app.services.chat_service import (
    get_chat_history,
    save_chat_exchange,
    clear_chat_history,
)

from app.services.document_service import (
    get_document_metadata,
    session_exists,
)

from app.services.llm_service import (
    build_rag_prompt,
    build_sources,
    get_chat_model,
    plan_retrieval_query,
)
from app.services.retrieval_service import (
    retrieve_relevant_chunks,
)
from app.utils.sse import sse_event

from app.core.redis import redis_client

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)


def extract_chunk_text(chunk) -> str:
    content = getattr(
        chunk,
        "content",
        "",
    )

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for item in content:
            if isinstance(item, str):
                text_parts.append(item)

            elif isinstance(item, dict):
                text = item.get("text")

                if isinstance(text, str):
                    text_parts.append(text)

        return "".join(text_parts)

    if isinstance(content, dict):
        text = content.get("text")

        if isinstance(text, str):
            return text

    return ""



@router.post("/{document_id}/ask")
async def ask_document_question(
    document_id: str,
    request: AskQuestionRequest,
):
    question = request.question.strip()

    if not question:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_question",
                "message": "Question cannot be empty.",
            },
        )

    if len(question) > 1000:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_question",
                "message": (
                    "Question must not exceed "
                    "1000 characters."
                ),
            },
        )

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

    if (
        metadata["session_id"]
        != request.session_id
    ):
        return JSONResponse(
            status_code=404,
            content={
                "error": "session_not_found",
            },
        )

    if not await session_exists(
        request.session_id
    ):
        return JSONResponse(
            status_code=404,
            content={
                "error": "session_not_found",
            },
        )

    try:
        chat_history = await get_chat_history(
            request.session_id,
            document_id,
        )

        retrieval_plan = (
            await plan_retrieval_query(
                question=request.question,
                chat_history=chat_history,
            )
        )

        retrieval_mode = (
            retrieval_plan["mode"]
        )

        retrieval_question = (
            retrieval_plan["query"]
        )

        print(
            f"[Retrieval] "
            f"mode={retrieval_mode} | "
            f"query={retrieval_question}"
        )

        results = await retrieve_relevant_chunks(
            document_id=document_id,
            question=retrieval_question,
            mode=retrieval_mode,
        )

    except Exception as exc:
        print(
            f"Retrieval failed: {exc}"
        )

        return JSONResponse(
            status_code=503,
            content={
                "error": "index_unavailable",
                "message": (
                    "Document index is "
                    "temporarily unavailable."
                ),
            },
        )

    message_id = (
        f"m_{uuid.uuid4().hex[:8]}"
    )

    start_timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    if not results:

        async def not_found_stream():
            answer = (
                "This information is not "
                "available in the uploaded "
                "document."
            )

            yield sse_event(
                "start",
                {
                    "message_id": message_id,
                    "timestamp": start_timestamp,
                },
            )

            yield sse_event(
                "token",
                {
                    "text": answer,
                },
            )

            await save_chat_exchange(
                session_id=request.session_id,
                document_id=document_id,
                question=question,
                answer=answer,
                sources=[],
                assistant_message_id=message_id,
            )

            yield sse_event(
                "sources",
                {
                    "sources": [],
                    "not_found": True,
                },
            )

            completion_timestamp = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            yield sse_event(
                "done",
                {
                    "message_id": message_id,
                    "timestamp": (
                        completion_timestamp
                    ),
                },
            )

        return StreamingResponse(
            not_found_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    prompt = build_rag_prompt(
        question=retrieval_question,
        results=results,
        chat_history=chat_history,
    )

    sources = build_sources(
        results
    )

    model = get_chat_model()

    async def answer_stream():
        full_answer_parts = []

        yield sse_event(
            "start",
            {
                "message_id": message_id,
                "timestamp": start_timestamp,
            },
        )

        try:
            async for chunk in model.astream(
                prompt
            ):
                text = extract_chunk_text(
                    chunk
                )

                if not text:
                    continue

                full_answer_parts.append(
                    text
                )

                yield sse_event(
                    "token",
                    {
                        "text": text,
                    },
                )

            full_answer = "".join(
                full_answer_parts
            )

            await save_chat_exchange(
                session_id=request.session_id,
                document_id=document_id,
                question=question,
                answer=full_answer,
                sources=sources,
                assistant_message_id=message_id,
            )

            yield sse_event(
                "sources",
                {
                    "sources": sources,
                },
            )

            completion_timestamp = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            yield sse_event(
                "done",
                {
                    "message_id": message_id,
                    "timestamp": (
                        completion_timestamp
                    ),
                },
            )

            print(
                f"[Chat {message_id}] "
                f"Completed answer: "
                f"{len(full_answer)} chars"
            )

        except Exception as exc:
            print(
                f"Gemini stream failed: {exc}"
            )

            yield sse_event(
                "error",
                {
                    "error": "llm_unavailable",
                    "message": (
                        "The answer stream was "
                        "interrupted. "
                        "Please retry."
                    ),
                    "retryable": True,
                },
            )

    return StreamingResponse(
        answer_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{session_id}/{document_id}/history"
)
async def get_session_chat_history(
    session_id: str,
    document_id: str,
):
    if not await session_exists(
        session_id
    ):
        return JSONResponse(
            status_code=404,
            content={
                "error": "session_not_found",
            },
        )

    # Refresh session expiry because export is activity
    await redis_client.expire(
        f"session:{session_id}",
        settings.SESSION_EXPIRY_SECONDS,
    )

    if document_id:
        await refresh_session_cleanup(
            session_id=session_id,
            document_id=document_id,
        )

    messages = await get_chat_history(
        session_id,
        document_id,
    )

    return {
        "session_id": session_id,
        "document_id": document_id,
        "messages": messages,
    }



# @router.post(
#     "/{session_id}/reset",
#     status_code=204,
# )
# async def reset_chat_history(
#     session_id: str,
# ):
#     if not await session_exists(
#         session_id
#     ):
#         return JSONResponse(
#             status_code=404,
#             content={
#                 "error": "session_not_found",
#             },
#         )

#     await clear_chat_history(
#         session_id
#     )

#     return Response(
#         status_code=204
#     )


@router.post(
    "/{session_id}/{document_id}/reset",
    status_code=204,
)
async def reset_chat_history(
    session_id: str,
    document_id: str,
):
    if not await session_exists(
        session_id
    ):
        return JSONResponse(
            status_code=404,
            content={
                "error": "session_not_found",
            },
        )

    await clear_chat_history(
        session_id,
        document_id,
    )

    await redis_client.expire(
        f"session:{session_id}",
        settings.SESSION_EXPIRY_SECONDS,
    )

    if document_id:
        await refresh_session_cleanup(
            session_id=session_id,
            document_id=document_id,
        )

    return Response(
        status_code=204
    )






@router.get(
    "/{session_id}/{document_id}/export"
)
async def export_chat_history(
    session_id: str,
    document_id: str,
    format: str = Query(default="txt"),
):
    if not await session_exists(
        session_id
    ):
        return JSONResponse(
            status_code=404,
            content={
                "error": "session_not_found",
            },
        )

    if format not in {"txt", "json"}:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_export_format",
                "message": (
                    "Export format must be "
                    "'txt' or 'json'."
                ),
            },
        )

    messages = await get_chat_history(
        session_id,
        document_id,
    )

    if format == "json":
        content = json.dumps(
            {
                "session_id": session_id,
                "document_id": document_id,
                "messages": messages,
            },
            indent=2,
        )

        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": (
                    'attachment; '
                    'filename="conversation.json"'
                ),
            },
        )

    lines = []

    for message in messages:
        role = message["role"].capitalize()

        lines.append(
            f"{role}: {message['content']}"
        )

        if (
            message["role"] == "assistant"
            and message.get("sources")
        ):
            source_labels = []

            for source in message["sources"]:
                if source["type"] == "page":
                    source_labels.append(
                        f"Page {source['number']}"
                    )

                elif source["type"] == "section":
                    label = (
                        f"Section "
                        f"{source['number']}"
                    )

                    heading = source.get(
                        "heading"
                    )

                    if heading:
                        label += (
                            f" - {heading}"
                        )

                    source_labels.append(
                        label
                    )

            if source_labels:
                lines.append(
                    "Sources: "
                    + ", ".join(
                        source_labels
                    )
                )

        lines.append("")

    content = "\n".join(lines)

    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": (
                'attachment; '
                'filename="conversation.txt"'
            ),
        },
    )
