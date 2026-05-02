from uuid import uuid4
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class RunNewsPipelineRequest(BaseModel):
    topic: str
    time_window_hours: int = Field(default=24, ge=1, le=168)
    max_stories: int = Field(default=10, ge=1, le=100)


@router.post("/run-news-pipeline")
async def run_news_pipeline(req: RunNewsPipelineRequest) -> dict[str, str]:
    _ = req
    return {"run_id": str(uuid4()), "status": "queued"}
