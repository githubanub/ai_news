import hashlib
import hmac
import time
from fastapi import HTTPException, Request


async def verify_slack_signature(request: Request, signing_secret: str) -> bytes:
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    slack_signature = request.headers.get("X-Slack-Signature")

    if not timestamp or not slack_signature:
        raise HTTPException(status_code=401, detail="Missing Slack signature headers")

    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise HTTPException(status_code=401, detail="Slack request timestamp too old")

    basestring = f"v0:{timestamp}:".encode("utf-8") + body
    computed = "v0=" + hmac.new(signing_secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, slack_signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    return body
