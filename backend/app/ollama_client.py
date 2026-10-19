import httpx


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def chat(
        self, *, messages: list[dict], tools: list[dict], model: str
    ) -> dict:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "tools": tools,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
