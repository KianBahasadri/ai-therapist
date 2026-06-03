from __future__ import annotations

import httpx

from backend.config import OPENROUTER_MODEL, Settings


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def complete(self, system: str, user: str, temperature: float = 0.3) -> str:
        if not self.settings.openrouter_api_key:
            return self._mock_complete(system, user)

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": self.settings.app_name,
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def _mock_complete(self, system: str, user: str) -> str:
        lower = (system + "\n" + user).lower()
        if "risk" in lower or "danger" in lower:
            return "No immediate crisis signal detected in the available text. Continue monitoring for self-harm, harm to others, abuse, coercion, or inability to stay safe."
        if "emotional state" in lower:
            return "The user appears engaged and is asking for implementation direction rather than describing current emotional distress."
        if "withholding" in lower:
            return "No strong sign of withheld clinical information. Ask concise follow-up questions only when needed."
        if "notes" in lower:
            return "User is building a web-based AI therapy research prototype. Current focus: implement v0.1 backend/frontend without Docker."
        return (
            "I can help with that. For v0.1, we should keep the first version simple: capture the message, "
            "track long-running context, run a few focused internal assessments, and respond in a grounded, supportive way. "
            "What would be most useful to work through first?"
        )
