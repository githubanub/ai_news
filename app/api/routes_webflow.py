from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class WebflowCreateDraftRequest(BaseModel):
    draft_id: str


@router.post("/create-draft")
async def create_draft(req: WebflowCreateDraftRequest) -> dict[str, str]:
    return {"webflow_item_id": f"draft_{req.draft_id}", "status": "draft_created"}
