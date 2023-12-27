import json
import logging
from typing import Any, Dict

import requests
from django.db.models import Q
from django.utils import timezone

from api.exceptions import OpenAIRequestException
from api.models import Log
from core.models import APIKey

logger = logging.getLogger("console")


class AICacheService:
    def __init__(self, base_url, endpoint, parameters, model):
        self.base_url = base_url
        self.endpoint = endpoint
        self.parameters = parameters
        self.model = model
        self.prepared_parameters = self.prepare_parameters()

    def run(self, apikey, user):
        if self.endpoint not in self.get_allowed_endpoints():
            raise OpenAIRequestException(detail="Invalid data")

        if not self.parameters:
            raise OpenAIRequestException(detail="Invalid data")

        log_instance = self.get_log_instance()

        if log_instance is not None:
            response = log_instance.response
            cache_hit = True
        else:
            started = timezone.now()
            logger.info(f"Calling API with {self.parameters} and apikey: {apikey}")
            response = json.dumps(self.get_api_response(apikey))
            finished = timezone.now()
            logger.debug(f"API response: {response}")
            logger.debug(f"API call took {finished - started}")

            cache_hit = False

        new_log_instance = self.create_log_instance(
            user=user,
            api_key=apikey,
            response=response,
            cache_hit=cache_hit,
        )

        return new_log_instance

    def get_allowed_endpoints(self):
        return [
            "v1/chat/completions",
            "v1/edits",
        ]

    def prepare_parameters(self):
        self.parameters['model'] = self.model
        return Log.jsonify_parameters(self.parameters)

    def create_log_instance(self, user, api_key, response, cache_hit):
        api_key_instance = APIKey.objects.get(key__exact=api_key)

        return Log.objects.create(
            endpoint=self.endpoint,
            parameters=self.prepared_parameters,
            user=user,
            api_key=api_key_instance,
            response=response,
            cache_hit=cache_hit,
        )

    def get_log_instance(self):
        return Log.objects.filter(
            self.create_logs_comparator(self.endpoint, self.prepared_parameters),
        ).first()

    @staticmethod
    def create_logs_comparator(endpoint, prepared_parameters) -> Q:
        return Q(
            endpoint=endpoint,
            parameters__exact=prepared_parameters,
        )

    def get_api_response(self, apikey):
        try:
            api_response = self.api_request(
                apikey=apikey, endpoint=self.endpoint, parameters=self.parameters
            )
        except OpenAIRequestException as exc:
            raise exc
        else:
            return api_response

    def api_request(self, apikey: str, endpoint: str, parameters: Dict[str, Any]):
        api_url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {apikey}",
        }

        try:
            response = requests.post(
                url=api_url, headers=headers, json=parameters
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OpenAIRequestException(detail=str(exc))
        else:
            return response.json()
