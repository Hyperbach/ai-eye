from typing import Any, Dict


def mock_openai_request(openaikey: str, endpoint: str, parameters: Dict[str, Any]):
    return f"OpenAI reply for {parameters['messages'][0]['content']}"
