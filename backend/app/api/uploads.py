from __future__ import annotations

import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.upload import UploadPresignRequest, UploadPresignResponse
from app.services.upload_service import generate_upload_presign

router = APIRouter(prefix="/uploads", tags=["uploads"])

logger = logging.getLogger(__name__)


@router.post(
    "/presign",
    response_model=UploadPresignResponse,
    status_code=status.HTTP_200_OK,
)
async def create_upload_presign(
    request: UploadPresignRequest,
    current_user: CurrentUser = Depends(get_current_user),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> UploadPresignResponse:
    request_id = x_request_id or str(uuid4())

    try:
        result = await generate_upload_presign(
            user_id=current_user.id,
            filename=request.filename,
            content_type=request.content_type,
            file_size_bytes=request.file_size_bytes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    logger.info(
        json.dumps(
            {
                "event": "upload_presign_created",
                "request_id": request_id,
                "user_id": str(current_user.id),
                "object_key": result.object_key,
                "service": "backend",
                "layer": "api",
            }
        )
    )

    return UploadPresignResponse(
        upload_url=result.upload_url,
        object_key=result.object_key,
        file_url=result.file_url,
        expires_in=result.expires_in,
        max_upload_size_bytes=result.max_upload_size_bytes,
        upload_headers=result.upload_headers,
    )
