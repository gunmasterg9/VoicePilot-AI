"""
NEO AI - LLM Provider Architecture
Provides provider-based language model integrations supporting:
1. Local Ollama models (with dynamic discovery, JSON error recovery, and offline resilience)
2. Optional Cloud LLM providers (OpenAI-compatible)
"""

import json
import re
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from config import OLLAMA_HOST, OLLAMA_MODEL
from core.prompts import SYSTEM_PROMPT
from core.settings import settings


class OllamaError(Exception):
    """Raised when communication with an LLM provider fails."""
    pass


def _extract_and_parse_json(content: str) -> Dict[str, Any]:
    """
    Robustly parses JSON responses from local LLMs.
    Handles Markdown code fences, extra text prefixes, and trailing comments.
    """
    text = content.strip()

    # 1. Strip Markdown code blocks if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # 2. Try direct json.loads
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 3. Extract bracketed JSON object via regex
    match = re.search(r"(\{[\s\S]*\})", text)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 4. Fallback: Wrap raw text in conversational response
    return {
        "type": "chat",
        "response": text,
        "actions": []
    }


class BaseLLMProvider(ABC):
    """Abstract interface for all LLM providers."""

    @abstractmethod
    def ask(self, user_message: str, conversation: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Send message to model and return structured JSON dictionary."""
        pass

    @abstractmethod
    def check_health(self) -> bool:
        """Return True if provider endpoint is reachable."""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """Return list of available models."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class OllamaProvider(BaseLLMProvider):
    """Primary local LLM provider connecting to Ollama."""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self._host = (host or settings.get("ollama_host", OLLAMA_HOST)).rstrip("/")
        self._configured_model = model or settings.get("ollama_model", OLLAMA_MODEL)
        self._resolved_model: Optional[str] = None
        self._cancelled = False

    @property
    def provider_name(self) -> str:
        return f"Ollama ({self.get_active_model()})"

    def cancel(self):
        """Signals cancellation of any ongoing in-flight request."""
        self._cancelled = True

    def check_health(self) -> bool:
        """Quick 2-second reachability probe."""
        request = urllib.request.Request(
            f"{self._host}/api/tags",
            method="GET"
        )
        try:
            with urllib.request.urlopen(request, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False

    def is_available(self) -> bool:
        return self.check_health()

    def list_models(self) -> List[str]:
        request = urllib.request.Request(
            f"{self._host}/api/tags",
            method="GET"
        )
        try:
            with urllib.request.urlopen(request, timeout=3.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return [m.get("name") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def set_model(self, model_name: str) -> None:
        self._configured_model = model_name
        self._resolved_model = model_name

    def get_active_model(self) -> str:
        if self._resolved_model:
            return self._resolved_model

        available = self.list_models()
        if not available:
            self._resolved_model = self._configured_model
            return self._resolved_model

        if self._configured_model in available:
            self._resolved_model = self._configured_model
            return self._resolved_model

        # Partial matching
        prefix = self._configured_model.split(":")[0]
        for m in available:
            if prefix in m:
                self._resolved_model = m
                return self._resolved_model

        # Prefer lightweight models optimized for 8 GB RAM
        lightweight_candidates = ["qwen3:1.7b", "smollm2:latest", "llama3.2:latest", "qwen2.5:7b"]
        for cand in lightweight_candidates:
            if cand in available:
                self._resolved_model = cand
                return self._resolved_model

        # Fall back to first available installed model
        self._resolved_model = available[0]
        return self._resolved_model

    def ask(self, user_message: str, conversation: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        self._cancelled = False

        # Build message history with configurable turn limits
        max_turns = int(settings.get("max_history_turns", 8))
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if conversation:
            # Sliding window of recent turns (each turn has user + assistant)
            recent_turns = conversation[-(max_turns * 2):]
            messages.extend(recent_turns)

        messages.append({"role": "user", "content": user_message})

        active_model = self.get_active_model()
        timeout = int(settings.get("llm_timeout", 45))

        payload = {
            "model": active_model,
            "messages": messages,
            "stream": False,
            "format": "json"
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if self._cancelled:
                    return {"type": "chat", "response": "Request cancelled by user.", "actions": []}
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise OllamaError(
                f"Cannot connect to Ollama at {self._host}. Please ensure Ollama is running."
            ) from exc
        except TimeoutError as exc:
            raise OllamaError(
                f"Ollama request timed out after {timeout} seconds."
            ) from exc
        except Exception as exc:
            raise OllamaError(f"Ollama request error: {exc}") from exc

        try:
            result = json.loads(raw)
            content = result["message"]["content"]
            return _extract_and_parse_json(content)
        except Exception as exc:
            raise OllamaError(f"Invalid model response: {exc}") from exc


class CloudLLMProvider(BaseLLMProvider):
    """Optional OpenAI-compatible cloud provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self._api_key = api_key if api_key is not None else settings.get("cloud_api_key", "")
        self._base_url = (base_url if base_url is not None else settings.get("cloud_base_url", "https://api.openai.com/v1")).rstrip("/")
        self._model = model if model is not None else settings.get("cloud_model", "gpt-4o-mini")

    @property
    def provider_name(self) -> str:
        return f"Cloud ({self._model})"

    def check_health(self) -> bool:
        return bool(self._api_key)

    def is_available(self) -> bool:
        return self.check_health()

    def list_models(self) -> List[str]:
        return [self._model]

    def ask(self, user_message: str, conversation: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        if not self._api_key:
            raise OllamaError("Cloud provider selected but no API key configured in Settings.")

        max_turns = int(settings.get("max_history_turns", 8))
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation:
            messages.extend(conversation[-(max_turns * 2):])
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self._model,
            "messages": messages,
            "response_format": {"type": "json_object"}
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
            result = json.loads(raw)
            content = result["choices"][0]["message"]["content"]
            return _extract_and_parse_json(content)
        except Exception as exc:
            raise OllamaError(f"Cloud LLM request failed: {exc}") from exc


class LLMManager:
    """Manages active LLM provider based on application configuration."""

    def __init__(self):
        self.ollama_provider = OllamaProvider()
        self.cloud_provider = CloudLLMProvider()

    def get_provider(self) -> BaseLLMProvider:
        provider_type = settings.get("ai_provider", "ollama").lower()
        if provider_type == "cloud" and self.cloud_provider.check_health():
            return self.cloud_provider
        return self.ollama_provider

    def get_active_provider(self) -> BaseLLMProvider:
        return self.get_provider()

    def get_active_model(self) -> str:
        provider = self.get_provider()
        if isinstance(provider, OllamaProvider):
            return provider.get_active_model()
        return getattr(provider, "_model", "Cloud Model")

    def cancel(self):
        """Cancel active in-flight request."""
        if isinstance(self.ollama_provider, OllamaProvider):
            self.ollama_provider.cancel()

    def ask(self, user_message: str, conversation: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        return self.get_provider().ask(user_message, conversation)

    def check_health(self) -> bool:
        return self.get_provider().check_health()

    def list_models(self) -> List[str]:
        return self.get_provider().list_models()


# Global manager instance
llm_manager = LLMManager()

# Backward-compatibility API exports
def check_ollama() -> bool:
    return llm_manager.ollama_provider.check_health()

def get_available_models() -> List[str]:
    return llm_manager.ollama_provider.list_models()

def get_active_model() -> str:
    return llm_manager.ollama_provider.get_active_model()

def ask_ollama(user_message: str, conversation: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    return llm_manager.ask(user_message, conversation)
