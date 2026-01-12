from shared.ai.clients.llm_client import LLMClient, LlmPriceTier, LlmProvider
from shared.server_settings import server_settings
from google import genai
from google.genai import types
from typing import Optional, List, Tuple, Any

def _dump(obj, depth=0, max_depth=6):
    if depth > max_depth:
        return "<MAX DEPTH>"

    if hasattr(obj, "model_dump"):
        return _dump(obj.model_dump(), depth + 1, max_depth)

    if hasattr(obj, "__dict__"):
        return {
            k: _dump(v, depth + 1, max_depth)
            for k, v in obj.__dict__.items()
        }

    if isinstance(obj, dict):
        return {
            k: _dump(v, depth + 1, max_depth)
            for k, v in obj.items()
        }

    if isinstance(obj, (list, tuple)):
        return [_dump(v, depth + 1, max_depth) for v in obj]

    return obj




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
        function_declarations: List[dict] = None,
    ) -> Tuple[str, List[dict[str, Any]]]:
        config = types.GenerateContentConfig(
        )
        function_declaration_names = set()
        if function_declarations is not None:
            tools = types.Tool(function_declarations=function_declarations)
            config.tools = [tools]
            function_declaration_names = set(function_declaration['name'] for function_declaration in function_declarations)
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

        function_call_responses = {}

        for candidate in response.candidates:
            if candidate.content is None:
                continue
            for part in candidate.content.parts:
                if part.function_call is not None and part.function_call.name in function_declaration_names and part.function_call.args:
                    function_call_responses[part.function_call.name] = part.function_call.args

        return response.text, function_call_responses
