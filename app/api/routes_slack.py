import json
from fastapi import APIRouter, HTTPException, Request
from app.config import settings
from app.integrations.slack_client import verify_slack_signature

router = APIRouter()


@router.post("/actions")
async def slack_actions(request: Request) -> dict[str, str]:
    if not settings.slack_signing_secret:
        raise HTTPException(status_code=500, detail="Slack signing secret is not configured")
    body = await verify_slack_signature(request, settings.slack_signing_secret)
    payload = request.query_params.get("payload")
    if payload is None:
        payload = dict((await request.form())).get("payload") if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded") else None
    if payload:
        _ = json.loads(payload)
    _ = body
    return {"status": "received"}
