from fastapi import APIRouter

router = APIRouter()


@router.get("/{draft_id}/preview")
async def preview_draft(draft_id: str) -> dict[str, str]:
    return {"draft_id": draft_id, "preview": "Not implemented"}
