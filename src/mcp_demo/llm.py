import os
import time
from pathlib import Path
from typing import cast

import logfire
from dotenv import load_dotenv
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import KnownModelName, Model, ModelRequestParameters
from pydantic_ai.models.gemini import GeminiModel, GeminiModelName
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import Usage

MAX_RETRIES = 3


class GeminiModelWithRetry(GeminiModel):
    """
    Gemini model that retries on 503 "Overloaded" errors
    """

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> tuple[ModelResponse, Usage]:
        retries = 0
        while True:
            try:
                return await super().request(messages, model_settings, model_request_parameters)
            except UnexpectedModelBehavior as e:
                if "503" in str(e) and "overloaded" in str(e):
                    retries += 1
                    if retries < MAX_RETRIES:
                        logfire.warn(
                            f"Model overloaded, retrying request {retries}/{MAX_RETRIES}",
                            retries=retries,
                            max_retries=MAX_RETRIES,
                        )
                        time.sleep(0.1)  # Wait 100ms before retry
                        continue
                raise


def build_model_from_name_and_api_key(model_name: KnownModelName | None, api_key: str | None = None) -> Model:
    """
    Build a model from a model name and API key.
    If no model name is provided, will try to infer from environment variables.
    """
    if not model_name:
        # Load environment variables from .env files
        # Try loading from home directory first, then current directory
        env_paths = [Path.home() / ".env", Path.cwd() / ".env"]

        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
            
        if os.environ.get("OPENAI_API_KEY"):
            logfire.info("Detected OPENAI_API_KEY, using openai:gpt-4o")
            model_name = "openai:gpt-4o"
            api_key = os.environ.get("OPENAI_API_KEY")
        elif os.environ.get("ANTHROPIC_API_KEY"):
            logfire.info("Detected ANTHROPIC_API_KEY, using anthropic:claude-3-7-sonnet-latest")
            model_name = "anthropic:claude-3-7-sonnet-latest"
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        elif os.environ.get("GEMINI_API_KEY"):
            logfire.info("Detected GEMINI_API_KEY, using google-gla:gemini-2.0-flash")
            model_name = "google-gla:gemini-2.0-flash"
            api_key = os.environ.get("GEMINI_API_KEY")
        else:
            raise ValueError("No model name provided and no API keys found in environment")

    assert model_name is not None

    # Add provider prefix if not present
    if isinstance(model_name, str) and model_name.startswith(("gpt-", "text-")):
        model_name = f"openai:{model_name}"
    elif isinstance(model_name, str) and model_name.startswith("claude-"):
        model_name = f"anthropic:{model_name}"
    elif isinstance(model_name, str) and model_name.startswith("gemini-"):
        model_name = f"google-gla:{model_name}"
    elif isinstance(model_name, str) and model_name.startswith(("llama-", "gemma")):
        model_name = f"groq:{model_name}"
    elif isinstance(model_name, str) and model_name.startswith("mistral-"):
        model_name = f"mistral:{model_name}"

    # api-key may be None still, but will be inferred from environment variables when initialising the model
    if isinstance(model_name, str) and model_name.startswith("openai:"):
        from pydantic_ai.models.openai import OpenAIModel

        return OpenAIModel(model_name[7:], api_key=api_key)

    elif isinstance(model_name, str) and model_name.startswith("anthropic:"):
        from pydantic_ai.models.anthropic import AnthropicModel

        return AnthropicModel(model_name[10:], api_key=api_key)

    elif isinstance(model_name, str) and model_name.startswith("google-gla:"):
        return GeminiModelWithRetry(cast(GeminiModelName, model_name[11:]), api_key=api_key)

    elif isinstance(model_name, str) and model_name.startswith("groq:"):
        from pydantic_ai.models.groq import GroqModel, GroqModelName

        return GroqModel(cast(GroqModelName, model_name[5:]), api_key=api_key)

    elif isinstance(model_name, str) and model_name.startswith("mistral:"):
        from pydantic_ai.models.mistral import MistralModel

        return MistralModel(model_name[8:], api_key=api_key)

    elif isinstance(model_name, str) and model_name.startswith("ollama:"):
        try:
            from pydantic_ai.models.ollama import OllamaModel

            return OllamaModel(model_name[7:], api_key=api_key or "ollama")
        except ImportError as e:
            raise ImportError("OllamaModel could not be imported. Ensure pydantic-ai[ollama] is installed.") from e

    else:
        raise ValueError(f"Unsupported model name: {model_name}")
