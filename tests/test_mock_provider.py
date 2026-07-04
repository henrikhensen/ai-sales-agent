from backend.infrastructure.llm.mock_provider import MockLLMProvider


async def test_mock_provider_builds_schema_conforming_object():
    provider = MockLLMProvider()
    schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "count": {"type": "integer"},
            "ratio": {"type": "number"},
            "flag": {"type": "boolean"},
            "items": {"type": "array"},
        },
        "required": ["text", "count"],
    }

    result = await provider.generate_json(
        system="system prompt",
        prompt="hello",
        schema=schema,
    )

    assert result == {
        "text": "[mock] hello",
        "count": len("hello"),
        "ratio": float(len("hello")),
        "flag": True,
        "items": [],
    }


async def test_mock_provider_handles_nested_objects():
    provider = MockLLMProvider()
    schema = {
        "type": "object",
        "properties": {
            "nested": {
                "type": "object",
                "properties": {"inner": {"type": "string"}},
            }
        },
    }

    result = await provider.generate_json(system="s", prompt="p", schema=schema)

    assert result == {"nested": {"inner": "[mock] p"}}


def test_mock_provider_name():
    assert MockLLMProvider().name == "mock"
