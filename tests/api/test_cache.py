from http import HTTPStatus
from typing import Any, Dict
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from api.models import Log
from rest_framework.test import APIClient

from tests.factories import (
    AiEyeAdminFactory,
    AiEyeUserFactory,
    OpenAIKeyFactory,
    PublicTokenFactory,
)


def openai_request_mock(openaikey: str, endpoint: str, parameters: Dict[str, Any]):
    # actually we don't care what response it returns because we test data caching only

    params_glued = "_".join([f"{k}_{v}" for k, v in parameters.items()])
    return f"{openaikey} {endpoint} {params_glued}"


class CacheTests(TestCase):
    def setUp(self) -> None:
        aieye_admin = AiEyeAdminFactory.create()
        aieye_user = AiEyeUserFactory.create()
        openaikey = OpenAIKeyFactory.create(owner=aieye_admin)

        self.aieye_admin = aieye_admin
        self.aieye_user = aieye_user
        self.openaikey = openaikey
        self.publictoken = PublicTokenFactory.create(
            user=aieye_user, openaikey=openaikey
        )

        self.client = APIClient()
        public_token = self.publictoken.key
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + public_token)

    def invoke_openai_api(self, request_data, endpoint):
        openai_api_url = reverse("api:openai-list", kwargs={"endpoint": endpoint})
        return self.client.post(openai_api_url, data=request_data)

    def invoke_cache_api(self, request_data, endpoint):
        cache_api_url = reverse("api:cache-list", kwargs={"endpoint": endpoint})
        return self.client.get(cache_api_url, data=request_data)

    def exec(self, request_data, endpoint):
        filter_kwargs = dict(
            endpoint=endpoint,
            parameters=Log.stringify_parameters(request_data),
            user=self.aieye_user,
        )

        caches_count_before = Log.objects.filter(**filter_kwargs).count()
        # there should be no cache before the request is performed
        self.assertEqual(caches_count_before, 0)

        response = self.invoke_openai_api(request_data, endpoint)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        caches_count_after = Log.objects.filter(**filter_kwargs).count()
        # there should be 1 cache record after the request is performed
        self.assertEqual(caches_count_after, 1)

        cache_hit_counts = Log.objects.filter(
            **filter_kwargs | {"cache_hit": True}
        ).count()
        cache_miss_counts = Log.objects.filter(
            **filter_kwargs | {"cache_hit": False}
        ).count()
        # there should be 0 cache hit records because the request is performed for the first time
        self.assertEqual(cache_hit_counts, 0)
        # there should be 1 cache miss records because the request is performed for the first time
        self.assertEqual(cache_miss_counts, 1)

        response = self.invoke_cache_api(request_data, endpoint)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # there should be 0 cache hits records in the API response
        self.assertEqual(len(response.data), 0)

        # perform a consequent request
        response = self.invoke_openai_api(request_data, endpoint)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        caches_count_after = Log.objects.filter(**filter_kwargs).count()
        # there should be 2 cache records in total after the consequent request is performed
        self.assertEqual(caches_count_after, 2)

        cache_hit_counts = Log.objects.filter(
            **filter_kwargs | {"cache_hit": True}
        ).count()
        cache_miss_counts = Log.objects.filter(
            **filter_kwargs | {"cache_hit": False}
        ).count()
        # there should be 1 cache hit records because the same request is performed for the second time
        self.assertEqual(cache_hit_counts, 1)
        # there should be 1 cache miss records, i.e. the very first request
        self.assertEqual(cache_miss_counts, 1)

        response = self.invoke_cache_api(request_data, endpoint)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # there should be 1 cache hits records in the API response now
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["cache_hit"], True)

    @patch("api.views.openai_request", side_effect=openai_request_mock)
    def test_cache_case1(self, mock_openai_request):
        request_data = {"model": "text-davinci-003", "prompt": "how do you do"}
        endpoint = "v1/completions"
        self.exec(request_data, endpoint)

    @patch("api.views.openai_request", side_effect=openai_request_mock)
    def test_cache_case_2(self, mock_openai_request):
        request_data = {"model": "text-davinci-003", "prompt": ""}
        endpoint = "v1/completions"
        self.exec(request_data, endpoint)

    @patch("api.views.openai_request", side_effect=openai_request_mock)
    def test_cache_case_3(self, mock_openai_request):
        request_data = {"model": "text-davinci-003", "prompt": "&"}
        endpoint = "v1/completions"
        self.exec(request_data, endpoint)
