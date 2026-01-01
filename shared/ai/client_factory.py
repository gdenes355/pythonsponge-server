from shared.models import AIProvider
from shared.ai.clients.gemini_client import GeminiClient
from shared.ai.clients.llm_client import LLMClient, LlmPriceTier
from shared.server_settings import server_settings

def get_llm_client(price_tier: LlmPriceTier = LlmPriceTier.LITE) -> LLMClient:
    if server_settings.ai_provider == AIProvider.GEMINI:
        return GeminiClient(price_tier=price_tier)
    else:
        raise ValueError(f"Unsupported provider: {server_settings.ai_provider}")
