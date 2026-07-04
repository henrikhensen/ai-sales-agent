from typing import Any

from backend.infrastructure.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Deterministic, network-free LLM provider for tests and local runs.

    Rather than calling a real model, it inspects the requested JSON Schema and
    synthesizes a conforming object by filling each property with a value
    derived from the prompt. This lets any agent be exercised end-to-end
    without external dependencies, and keeps outputs fully deterministic.
    """

    name = "mock"

    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        return self._build_object(schema, prompt)

    def _build_object(self, schema: dict[str, Any], prompt: str) -> dict[str, Any]:
        properties: dict[str, Any] = schema.get("properties", {})
        return {
            key: self._value_for(prop_schema, prompt)
            for key, prop_schema in properties.items()
        }

    def _value_for(self, prop_schema: dict[str, Any], prompt: str) -> Any:
        json_type = prop_schema.get("type")
        if json_type == "string":
            return f"[mock] {prompt}"
        if json_type == "integer":
            return len(prompt)
        if json_type == "number":
            return float(len(prompt))
        if json_type == "boolean":
            return True
        if json_type == "array":
            return []
        if json_type == "object":
            return self._build_object(prop_schema, prompt)
        return None
