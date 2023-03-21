from typing import Any, Dict

import requests
from api.exceptions import OpenAIRequestException

OPENAI_HOST = "https://api.openai.com"


def openai_request(openaikey: str, endpoint: str, parameters: Dict[str, Any]):
    openai_api_url = f"{OPENAI_HOST}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openaikey}",
    }

    try:
        response = requests.post(url=openai_api_url, headers=headers, json=parameters)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OpenAIRequestException(detail=str(exc))
    else:
        response_json = response.json()

        try:
            return response_json["choices"][0]["message"]["content"].strip()
        except (KeyError, ValueError) as exc:
            raise OpenAIRequestException(detail=str(exc))
