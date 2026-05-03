from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.pipeline_service import run_news_pipeline_now

router = APIRouter()


class RunNewsPipelineRequest(BaseModel):
    topic: str
    time_window_hours: int = Field(default=24, ge=1, le=168)
    max_stories: int = Field(default=10, ge=1, le=100)
    skip_duplicate_check: bool = True


@router.post("/run-news-pipeline")
async def run_news_pipeline(req: RunNewsPipelineRequest) -> dict:
    return run_news_pipeline_now(req.topic, req.time_window_hours, req.max_stories, skip_duplicate_check=req.skip_duplicate_check)
