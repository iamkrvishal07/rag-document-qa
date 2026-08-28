from pathlib import Path

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

from app.core.config import settings


def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
    )


def get_chroma_directory(
    document_id: str,
) -> Path:
    return (
        Path(settings.CHROMA_DIR)
        / document_id
    )


def create_document_index(
    *,
    document_id: str,
    chunks: list[Document],
) -> Chroma:
    persist_directory = get_chroma_directory(
        document_id
    )

    persist_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    embedding_model = get_embedding_model()

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        collection_name=f"document_{document_id}",
        persist_directory=str(
            persist_directory
        ),
    )

    return vector_store