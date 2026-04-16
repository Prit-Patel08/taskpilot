from fastapi import APIRouter

from app.api.placeholder import raise_placeholder

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/session")
async def session() -> None:
    raise_placeholder(
        "TODO: Backend-managed Auth0 session endpoint is not implemented yet."
    )


@router.post("/login")
async def login() -> None:
    raise_placeholder(
        "TODO: Backend-managed Auth0 login endpoint is not implemented yet."
    )


@router.post("/signup")
async def signup() -> None:
    raise_placeholder(
        "TODO: Backend-managed Auth0 signup endpoint is not implemented yet."
    )


@router.post("/logout")
async def logout() -> None:
    raise_placeholder(
        "TODO: Backend-managed Auth0 logout endpoint is not implemented yet."
    )
