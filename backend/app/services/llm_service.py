import ast
import json
import re

from langchain_google_genai import (
    ChatGoogleGenerativeAI,
)

from app.core.config import settings


def _extract_response_text(content) -> str:
    """
    Gemini/LangChain response.content can sometimes be a
    string and sometimes structured content blocks.
    """

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)

            elif isinstance(item, dict):
                text = item.get("text")

                if text:
                    parts.append(str(text))

        return "\n".join(parts).strip()

    return str(content).strip()


def _parse_retrieval_plan(
    content: str,
    question: str,
) -> dict:
    """
    Parse Gemini retrieval-planner output safely.

    Supports:
    - valid JSON
    - ```json fenced JSON
    - JSON surrounded by text
    - Python-style dict with single quotes
    """

    content = content.strip()

    # Remove markdown code fences.
    content = re.sub(
        r"^```(?:json)?\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"\s*```$",
        "",
        content,
    )

    content = content.strip()

    # Extract {...} if Gemini added surrounding text.
    match = re.search(
        r"\{.*\}",
        content,
        flags=re.DOTALL,
    )

    candidate = (
        match.group(0)
        if match
        else content
    )

    plan = None

    # First: proper JSON.
    try:
        plan = json.loads(candidate)

    except (json.JSONDecodeError, TypeError):
        pass

    # Second: Gemini may occasionally produce:
    #
    # {'mode': 'focused', 'query': '...'}
    #
    # which is a Python-style dict, not valid JSON.
    if plan is None:
        try:
            parsed = ast.literal_eval(candidate)

            if isinstance(parsed, dict):
                plan = parsed

        except (
            ValueError,
            SyntaxError,
        ):
            pass

    if not isinstance(plan, dict):
        raise ValueError(
            "Could not parse retrieval plan."
        )

    mode = str(
        plan.get(
            "mode",
            "focused",
        )
    ).lower().strip()

    query = str(
        plan.get(
            "query",
            question,
        )
    ).strip()

    if mode not in {
        "focused",
        "broad",
        "comparative",
    }:
        mode = "focused"

    if not query:
        query = question

    return {
        "mode": mode,
        "query": query,
    }


def get_chat_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
    )


async def plan_retrieval_query(
    *,
    question: str,
    chat_history: list[dict],
) -> dict:
    """
    Convert a natural-language question into a generic
    retrieval plan.

    Modes:
    - focused: specific factual/explanatory question
    - broad: document-wide summary/key-points question
    - comparative: comparison/ranking/judgement requiring
      evidence from multiple parts of the document
    """

    recent_history = chat_history[-4:]

    history_lines = []

    for message in recent_history:
        role = message.get(
            "role",
            "unknown",
        )

        content = message.get(
            "content",
            "",
        )

        if content:
            history_lines.append(
                f"{role}: {content}"
            )

    history_text = (
        "\n".join(history_lines)
        if history_lines
        else "No previous conversation."
    )

    prompt = f"""
You are a retrieval planner for a document question-answering
system.

The uploaded document may be ANY kind of document:
resume, notes, textbook, research paper, report,
documentation, article, policy, financial document,
technical document, or other text.

Your job is NOT to answer the question.

Your job is to create a retrieval plan.

Return ONLY valid JSON in exactly this structure:

{{
  "mode": "focused",
  "query": "semantic retrieval query"
}}

Allowed modes:

1. "focused"
Use when the question asks about a specific fact, concept,
definition, person, item, event, number, process, explanation,
or narrow topic.

Examples:
"What is useState?"
"What is the CGPA?"
"Where did he intern?"
"Explain inflation."
"What technologies are used?"

2. "broad"
Use when the question requires information from many parts
of the document or asks for an overall summary.

Examples:
"Summarize this document."
"What should I remember?"
"What are the important points?"
"Give me the main takeaways."
"What is this document about?"

For broad questions, rewrite the query using concepts such as:
key points, important ideas, main concepts, definitions,
examples, conclusions, takeaways, major topics.

3. "comparative"
Use when the user asks to compare, rank, judge, choose,
evaluate, or identify the strongest/best/most important
option based on multiple pieces of document evidence.

Examples:
"How is useEffect different from useState?"
"Which project is strongest?"
"Which option is better?"
"Compare these approaches."

For comparative questions, include all relevant concepts
and comparison criteria implied by the user.

General rules:

- Preserve the user's intended topic.
- Resolve vague references like "it", "this", "that",
  "he", "she", "they", "those" using recent conversation.
- Expand vague wording into semantic terms useful for
  document retrieval.
- Do not assume a particular document type.
- Do not invent names or facts.
- Do not answer the question.
- Return only JSON.
- Keep the query concise but retrieval-friendly.

Conversation history:
{history_text}

Current question:
{question}
"""

    try:
        model = get_chat_model()

        response = await model.ainvoke(
            prompt
        )

        content = _extract_response_text(
            response.content
        )

        return _parse_retrieval_plan(
            content,
            question,
        )

    except Exception as exc:
        print(
            "Retrieval planning failed: "
            f"{exc}"
        )

        return {
            "mode": "focused",
            "query": question,
        }


def build_sources(
    results,
) -> list[dict]:
    sources = []
    seen = set()

    for document, _score in results:
        metadata = document.metadata

        if metadata.get("file_type") == "pdf":
            number = metadata.get(
                "page_number"
            )

            if number is None:
                continue

            key = (
                "page",
                number,
            )

            if key in seen:
                continue

            seen.add(key)

            sources.append(
                {
                    "type": "page",
                    "number": number,
                }
            )

            continue

        if metadata.get("file_type") == "docx":
            number = metadata.get(
                "section_index"
            )

            if number is None:
                continue

            key = (
                "section",
                number,
            )

            if key in seen:
                continue

            seen.add(key)

            source = {
                "type": "section",
                "number": number,
            }

            heading = metadata.get(
                "section_heading"
            )

            if heading:
                source["heading"] = heading

            sources.append(source)

    return sources


def build_rag_prompt(
    *,
    question: str,
    results,
    chat_history: list[dict] | None = None,
) -> str:
    context_parts = []

    for index, (
        document,
        _score,
    ) in enumerate(
        results,
        start=1,
    ):
        metadata = document.metadata

        if metadata.get("file_type") == "pdf":
            page_number = metadata.get(
                "page_number"
            )

            location = (
                f"Page {page_number}"
            )

        else:
            section_number = (
                metadata.get(
                    "section_index"
                )
            )

            heading = metadata.get(
                "section_heading"
            )

            location = (
                f"Section {section_number}"
            )

            if heading:
                location += (
                    f" - {heading}"
                )

        context_parts.append(
            f"[Retrieved Chunk {index} - "
            f"{location}]\n"
            f"{document.page_content}"
        )

    context = "\n\n".join(
        context_parts
    )

    history_parts = []

    if chat_history:
        for message in chat_history[-4:]:
            role = (
                "User"
                if message.get("role") == "user"
                else "Assistant"
            )

            content = message.get(
                "content",
                "",
            )

            history_parts.append(
                f"{role}: {content}"
            )

    conversation_history = (
        "\n".join(history_parts)
        if history_parts
        else "No previous conversation."
    )

    return f"""
You are a document Q&A assistant.

Answer the user's current question using ONLY the
provided document context.

You may combine and synthesize facts from multiple
retrieved passages when they directly support the answer.

You may also make simple classifications, summaries,
comparisons, or conclusions that are directly supported
by the wording, structure, or content of the retrieved
document context.

For example, if the user asks what the document is mainly
about, what it is trying to communicate, what type of
content it is, or asks for its key takeaway, you may infer
that directly from the supplied document text even when
the exact answer is not written word-for-word.

Do not introduce external factual knowledge or unsupported
claims.

The conversation history is provided only to help
understand follow-up references such as "this",
"it", "that", "they", or similar references.

Write the answer in a clear, natural, and well-structured
way.

Do not include page numbers, section numbers, chunk labels,
source labels, or citations inside the written answer.

Do not write things such as "(Page 2)", "[Page 2]",
"according to Page 2", or "(Section 3)".

The application displays retrieved sources separately.

Use Markdown when it improves readability.

For comparison questions, clearly separate the concepts
using bullet points or short sections.

For explanatory questions:
- Start with a direct answer.
- Then explain the important details.
- Use bullet points when there are multiple ideas.
- Avoid unnecessary repetition.
- Keep the response concise but complete.

Only when the retrieved context genuinely does not contain
enough information to answer the question, respond exactly:

"This information is not available in the uploaded document."

Conversation History:
{conversation_history}

Document Context:
{context}

Current Question:
{question}
""".strip()
