from shared.ai.clients.llm_client import LLMClient, LlmPriceTier, LlmProvider
from shared.server_settings import server_settings
from google import genai
from google.genai import types
from typing import Optional


class GeminiClient(LLMClient):
    __models = {
        LlmPriceTier.LITE: "gemini-2.5-flash-lite",
        LlmPriceTier.STANDARD: "gemini-2.5-flash",
        LlmPriceTier.PRO: "gemini-2.5-pro",
    }

    def __new__(cls, price_tier: LlmPriceTier = LlmPriceTier.LITE):
        if not hasattr(cls, 'instances'):
            cls.instances = {}
        if price_tier not in cls.instances:
            cls.instances[price_tier] = super(GeminiClient, cls).__new__(cls)
            cls.instances[price_tier].__instance_init(price_tier)
        return cls.instances[price_tier]

    def __init__(self, price_tier: LlmPriceTier = LlmPriceTier.LITE):
        super().__init__(LlmProvider.GEMINI, self.__price_tier)

    def __instance_init(self, price_tier: LlmPriceTier):
        self.__price_tier = price_tier
        self.__api_key = server_settings.gemini_api_key
        self.__model = self.__models[price_tier]
        self.__client = genai.Client(api_key=self.__api_key) if self.__api_key else None

    def generate_text(
        self, 
        system_prompt: str, 
        prompt: str, 
        thinking_level: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        config = types.GenerateContentConfig(
        )
        if thinking_level is not None:
            config.thinking_config = types.ThinkingConfig(
                thinking_budget=thinking_level,
            )
        if temperature is not None:
            config.temperature = temperature
        if system_prompt is not None:
            config.system_instruction = system_prompt
        response = self.__client.models.generate_content(
            model=self.__model,
            contents=[prompt],
            config=config,
        )
            
        return response.text
