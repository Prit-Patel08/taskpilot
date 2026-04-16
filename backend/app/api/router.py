from fastapi import APIRouter

from app.api.applications import router as applications_router
from app.api.auth import router as auth_router
from app.api.job_listings import router as job_listings_router
from app.api.jobs import router as jobs_router
from app.api.resumes import router as resumes_router
from app.api.uploads import router as uploads_router

api_router = APIRouter()
api_router.include_router(applications_router)
api_router.include_router(auth_router)
api_router.include_router(job_listings_router)
api_router.include_router(jobs_router)
api_router.include_router(resumes_router)
api_router.include_router(uploads_router)
