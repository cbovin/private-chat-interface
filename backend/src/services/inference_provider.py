"""
Inference provider service with strategy pattern for multiple providers.
"""
import abc
from typing import Dict, List, Optional, Any
from enum import Enum

import openai
import httpx

from src.core.config import settings


class InferenceProviderType(str, Enum):
    """Supported inference provider types."""
    OPENAI = "openai"
    VLLM = "vllm"


class InferenceRequest:
    """Standardized inference request."""

    def __init__(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        self.messages = messages
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs


class InferenceResponse:
    """Standardized inference response."""

    def __init__(
        self,
        content: str,
        model: str,
        usage: Optional[Dict[str, int]] = None,
        **kwargs
    ):
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.kwargs = kwargs


class InferenceProvider(abc.ABC):
    """Abstract base class for inference providers."""

    @abc.abstractmethod
    async def generate(self, request: InferenceRequest) -> InferenceResponse:
        """Generate response for the given request."""
        pass

    @abc.abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass

    @property
    @abc.abstractmethod
    def provider_type(self) -> InferenceProviderType:
        """Get provider type."""
        pass


class OpenAIProvider(InferenceProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key != "mock-key":
            self.client = openai.AsyncOpenAI(api_key=api_key)
        else:
            self.client = None

    async def generate(self, request: InferenceRequest) -> InferenceResponse:
        """Generate response using OpenAI API."""
        # Handle mock responses for testing
        if self.api_key == "mock-key":
            return InferenceResponse(
                content="This is a mock AI response for testing purposes. The actual LLM integration is not configured yet.",
                model="mock-model",
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            )

        try:
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                **request.kwargs
            )

            return InferenceResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    def get_available_models(self) -> List[str]:
        """Get available OpenAI models."""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]

    @property
    def provider_type(self) -> InferenceProviderType:
        return InferenceProviderType.OPENAI


class VLLMProvider(InferenceProvider):
    """VLLM inference provider."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")
        self.client = httpx.AsyncClient(timeout=300.0)

    async def generate(self, request: InferenceRequest) -> InferenceResponse:
        """Generate response using VLLM API."""
        try:
            payload = {
                "model": request.model,
                "messages": request.messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                **request.kwargs
            }

            response = await self.client.post(
                f"{self.endpoint}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            data = response.json()

            return InferenceResponse(
                content=data["choices"][0]["message"]["content"],
                model=data["model"],
                usage=data.get("usage", {})
            )
        except Exception as e:
            raise Exception(f"VLLM API error: {str(e)}")

    def get_available_models(self) -> List[str]:
        """Get available VLLM models."""
        # This would typically query the VLLM server for available models
        return ["default-model"]  # Placeholder

    @property
    def provider_type(self) -> InferenceProviderType:
        return InferenceProviderType.VLLM


class InferenceProviderFactory:
    """Factory for creating inference providers."""

    @staticmethod
    def create_provider(provider_type: InferenceProviderType, **kwargs) -> InferenceProvider:
        """Create an inference provider instance."""
        if provider_type == InferenceProviderType.OPENAI:
            api_key = kwargs.get("api_key") or settings.openai_api_key
            if not api_key and api_key != "mock-key":
                raise ValueError("OpenAI API key is required")
            return OpenAIProvider(api_key or "mock-key")

        elif provider_type == InferenceProviderType.VLLM:
            endpoint = kwargs.get("endpoint") or settings.vllm_endpoint
            if not endpoint:
                raise ValueError("VLLM endpoint is required")
            return VLLMProvider(endpoint)

        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")


class InferenceService:
    """Main inference service with provider management."""

    def __init__(self):
        self.providers: Dict[str, InferenceProvider] = {}
        self.workspace_providers: Dict[str, str] = {}  # workspace_id -> provider_name

    def register_provider(
        self,
        name: str,
        provider_type: InferenceProviderType,
        **kwargs
    ) -> None:
        """Register an inference provider."""
        provider = InferenceProviderFactory.create_provider(provider_type, **kwargs)
        self.providers[name] = provider

    def set_workspace_provider(self, workspace_id: str, provider_name: str) -> None:
        """Set the inference provider for a workspace."""
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not registered")
        self.workspace_providers[workspace_id] = provider_name

    def get_provider_for_workspace(self, workspace_id: str) -> InferenceProvider:
        """Get the inference provider for a workspace."""
        provider_name = self.workspace_providers.get(workspace_id, settings.default_inference_provider)

        if provider_name not in self.providers:
            # Fallback to default provider
            provider_name = settings.default_inference_provider
            if provider_name not in self.providers:
                raise ValueError(f"No provider available for workspace {workspace_id}")

        return self.providers[provider_name]

    async def generate(
        self,
        request: InferenceRequest,
        workspace_id: Optional[str] = None
    ) -> InferenceResponse:
        """Generate inference response."""
        if workspace_id:
            provider = self.get_provider_for_workspace(workspace_id)
        else:
            # Use default provider
            provider_name = settings.default_inference_provider
            if provider_name not in self.providers:
                raise ValueError("No default provider configured")
            provider = self.providers[provider_name]

        return await provider.generate(request)

    def get_available_providers(self) -> List[str]:
        """Get list of registered provider names."""
        return list(self.providers.keys())

    def get_provider_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a provider."""
        if name not in self.providers:
            return None

        provider = self.providers[name]
        return {
            "type": provider.provider_type.value,
            "models": provider.get_available_models()
        }


# Global inference service instance
inference_service = InferenceService()

# Initialize default providers
if settings.openai_api_key:
    inference_service.register_provider(
        "openai",
        InferenceProviderType.OPENAI,
        api_key=settings.openai_api_key
    )

if settings.vllm_endpoint:
    inference_service.register_provider(
        "vllm",
        InferenceProviderType.VLLM,
        endpoint=settings.vllm_endpoint
    )

# Add a mock provider for testing when no real providers are available
if not settings.openai_api_key and not settings.vllm_endpoint:
    inference_service.register_provider(
        "mock",
        InferenceProviderType.OPENAI,  # Use OpenAI type but with mock implementation
        api_key="mock-key"
    )
    inference_service.set_workspace_provider("default", "mock")
