"""
Thin async client for a locally-served, open-weight LLM via Ollama
(https://ollama.com). Everything here talks to OLLAMA_BASE_URL — by
default http://localhost:11434 — and nowhere else. No API key, because
there's no external API: the model runs on this machine.

MOCK_LLM (or Ollama simply being unreachable) makes every call fall back
to a deterministic, clearly-labelled canned response, so the rest of the
stack — routing, retrieval, guardrails, the trace panel, the frontend —
can be built, tested and demoed before anyone has pulled multi-gigabyte
model weights onto the demo laptop. Flip MOCK_LLM=false in .env once
`ollama pull llama3.1:8b` (and, for the vision agent, `ollama pull
llava`) have finished.
"""
from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("workbench.llm")
settings = get_settings()

Message = dict[str, str]  # {"role": "user"|"assistant"|"system", "content": "..."}


class LLMUnavailableError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.text_model = settings.OLLAMA_TEXT_MODEL
        self.vision_model = settings.OLLAMA_VISION_MODEL
        self.timeout = settings.LLM_REQUEST_TIMEOUT_SECONDS

    async def _post_chat(self, model: str, messages: list[Message]) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {"model": model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()

    async def chat(self, messages: list[Message], *, model: str | None = None) -> str:
        if settings.MOCK_LLM:
            return _mock_text_reply(messages)
        try:
            return await self._post_chat(model or self.text_model, messages)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("Ollama unreachable (%s) — falling back to mock reply.", exc)
            return _mock_text_reply(messages, degraded=True)

    async def chat_vision(self, prompt: str, image_base64: str, *, model: str | None = None) -> str:
        if settings.MOCK_LLM:
            return _mock_vision_reply(prompt)
        messages = [{"role": "user", "content": prompt, "images": [image_base64]}]
        try:
            return await self._post_chat(model or self.vision_model, messages)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("Ollama vision call failed (%s) — falling back to mock reply.", exc)
            return _mock_vision_reply(prompt, degraded=True)

    async def health(self) -> bool:
        """Used by /api/health — never raises, just reports reachability."""
        if settings.MOCK_LLM:
            return True
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _mock_text_reply(messages: list[Message], *, degraded: bool = False) -> str:
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    prefix = "[MOCK — Ollama unreachable, showing a stand-in reply] " if degraded else "[MOCK MODE] "
    return (
        f"{prefix}Based on the retrieved passages, here is a draft answer to: "
        f'"{last_user[:200]}". Set MOCK_LLM=false and point OLLAMA_BASE_URL at a running '
        f"Ollama instance with the model pulled to get a real, grounded answer here."
    )


def _mock_vision_reply(prompt: str, *, degraded: bool = False) -> str:
    prefix = "[MOCK — Ollama unreachable] " if degraded else "[MOCK MODE] "
    return (
        f"{prefix}(Vision agent) I would describe the uploaded diagram/image here and answer: "
        f'"{prompt[:150]}". Pull a vision model (e.g. `ollama pull llava`) and set MOCK_LLM=false '
        f"for a real multimodal reading of the image."
    )


_client: OllamaClient | None = None


def get_llm_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
