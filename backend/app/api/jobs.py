from fastapi import APIRouter

from app.api.placeholder import raise_placeholder

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/search")
async def search_jobs() -> None:
    raise_placeholder(
        "TODO: Backend job search endpoint is not implemented yet."
    )


@router.get("/companies")
async def list_companies() -> None:
    raise_placeholder(
        "TODO: Backend company filter endpoint is not implemented yet."
    )
