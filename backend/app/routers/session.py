from fastapi import APIRouter

from app.services.document_service import (
    create_session,
)


router = APIRouter(
    tags=["session"],
)


@router.post(
    "/session",
    status_code=201,
)
async def create_guest_session():
    return await create_session()
