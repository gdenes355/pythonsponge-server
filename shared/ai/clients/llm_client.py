from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Optional, Tuple, List, Any

class LlmProvider(StrEnum):
    GEMINI = "GEMINI"

class LlmPriceTier(StrEnum):
    LITE = "LITE"  # lite or mini models
    STANDARD = "STANDARD"  # standard models
    PRO = "PRO"  # pro models

class LLMClient:
    def __init__(self, provider: LlmProvider, price_tier: LlmPriceTier):
        self.__provider = provider
        self.__price_tier = price_tier

    @property
    def price_tier(self) -> LlmPriceTier:
        return self.__price_tier

    @property
    def provider(self) -> LlmProvider:
        return self.__provider

    @abstractmethod
    def generate_text(
        self, 
        system_prompt: str, 
        prompt: str, 
        thinking_level: Optional[int] = None,
        temperature: Optional[float] = None,
        function_declarations: List[dict] = None,
        force_function_calls: bool = False,
    ) -> Tuple[str, List[dict[str, Any]]]:
        pass
