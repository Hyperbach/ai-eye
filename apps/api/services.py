from typing import Any, Dict

from django.db.models import Q

import requests
from api.exceptions import OpenAIRequestException
from api.models import Log
from core.models import OpenAIKey


class OpenAICacheService:
    OPENAI_HOST = "https://api.openai.com"

    ALLOWED_OPENAI_ENDPOINTS = [
        "v1/chat/completions",
        "v1/edits",
    ]

    def __init__(self, endpoint, parameters):
        self.endpoint = endpoint
        self.parameters = parameters
        self.prepared_parameters = self.prepare_parameters()

    def run(self, openaikey, user):
        if self.endpoint not in self.ALLOWED_OPENAI_ENDPOINTS:
            raise OpenAIRequestException(detail="Invalid data")

        if not self.parameters:
            raise OpenAIRequestException(detail="Invalid data")

        log_instance = self.get_log_instance()

        if log_instance is not None:
            response = log_instance.response
            cache_hit = True
        else:
            response = self.get_openai_response(openaikey)
            cache_hit = False

        new_log_instance = self.create_log_instance(
            user=user,
            api_key=openaikey,
            response=response,
            cache_hit=cache_hit,
        )

        return new_log_instance

    def prepare_parameters(self):
        return Log.jsonify_parameters(self.parameters)

    def create_log_instance(self, user, api_key, response, cache_hit):
        openai_key_instance = OpenAIKey.objects.get(key__exact=api_key)

        return Log.objects.create(
            endpoint=self.endpoint,
            parameters=self.prepared_parameters,
            user=user,
            api_key=openai_key_instance,
            response=response,
            cache_hit=cache_hit,
        )

    def get_log_instance(self):
        return Log.objects.filter(
            self.create_logs_comparator(),
        ).first()

    def create_logs_comparator(self) -> Q:
        return Q(
            endpoint=self.endpoint,
            parameters__exact=self.prepared_parameters,
        )

    def get_openai_response(self, openaikey):
        try:
            openai_response = self.openai_request(
                openaikey=openaikey, endpoint=self.endpoint, parameters=self.parameters
            )
        except OpenAIRequestException as exc:
            raise exc
        else:
            return openai_response

    def openai_request(self, openaikey: str, endpoint: str, parameters: Dict[str, Any]):
        openai_api_url = f"{self.OPENAI_HOST}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openaikey}",
        }

        try:
            response = requests.post(
                url=openai_api_url, headers=headers, json=parameters
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OpenAIRequestException(detail=str(exc))
        else:
            response_json = response.json()

            try:
                return response_json["choices"][0]["message"]["content"].strip()
            except (KeyError, ValueError) as exc:
                raise OpenAIRequestException(detail=str(exc))
