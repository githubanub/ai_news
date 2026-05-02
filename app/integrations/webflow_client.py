import httpx


class WebflowClient:
    def __init__(self, api_token: str, collection_id: str):
        self.api_token = api_token
        self.collection_id = collection_id
        self.base_url = "https://api.webflow.com/v2"

    async def create_draft_item(self, payload: dict) -> dict:
        url = f"{self.base_url}/collections/{self.collection_id}/items"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
