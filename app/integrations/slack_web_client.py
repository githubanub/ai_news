from typing import Any

import httpx


class SlackWebClient:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = "https://slack.com/api"

    def post_message(self, channel_id: str, text: str, blocks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload: dict[str, Any] = {"channel": channel_id, "text": text}
        if blocks:
            payload["blocks"] = blocks

        with httpx.Client(timeout=30) as client:
            response = client.post(f"{self.base_url}/chat.postMessage", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise RuntimeError(str(data.get("error", "Slack API request failed")))
        return data

    def post_ephemeral(self, channel_id: str, user_id: str, text: str) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload: dict[str, Any] = {"channel": channel_id, "user": user_id, "text": text}

        with httpx.Client(timeout=30) as client:
            response = client.post(f"{self.base_url}/chat.postEphemeral", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise RuntimeError(str(data.get("error", "Slack API request failed")))
        return data

    def update_message(self, channel_id: str, message_ts: str, text: str, blocks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload: dict[str, Any] = {"channel": channel_id, "ts": message_ts, "text": text}
        if blocks:
            payload["blocks"] = blocks

        with httpx.Client(timeout=30) as client:
            response = client.post(f"{self.base_url}/chat.update", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise RuntimeError(str(data.get("error", "Slack API request failed")))
        return data
