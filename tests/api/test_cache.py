from http import HTTPStatus
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from api.models import Log
from parameterized import parameterized
from rest_framework.test import APIClient

from tests.factories import (
    AiEyeAdminFactory,
    AiEyeUserFactory,
    OpenAIKeyFactory,
    PublicTokenFactory,
)
from tests.mocks import mock_openai_request


class CacheTests(TestCase):
    def setUp(self) -> None:
        aieye_admin = AiEyeAdminFactory.create()
        openaikey = OpenAIKeyFactory.create(owner=aieye_admin)
        self.aieye_user = AiEyeUserFactory.create()
        publictoken = PublicTokenFactory.create(
            user=self.aieye_user, openaikey=openaikey
        )

        self.client = APIClient()
        public_token = publictoken.key
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + public_token)

    def invoke_openai_api(self, request_data, endpoint):
        openai_api_url = reverse("api:openai-list", kwargs={"endpoint": endpoint})
        return self.client.post(openai_api_url, data=request_data, format="json")

    def invoke_cache_api(self, request_data, endpoint):
        cache_api_url = reverse("api:cache", kwargs={"endpoint": endpoint})
        return self.client.post(cache_api_url, data=request_data, format="json")

    def exec(self, request_data, endpoint):
        filter_kwargs = dict(
            endpoint=endpoint,
            parameters=Log.jsonify_parameters(request_data),
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

    @parameterized.expand(
        [
            [
                {
                    "model": "gpt-3.5-turbo-1106",
                    "messages": [{"role": "user", "content": "how do you do?"}],
                }
            ],
            [{"model": "gpt-3.5-turbo-1106", "messages": [{"role": "user", "content": ""}]}],
            [
                {
                    "model": "gpt-3.5-turbo-1106",
                    "messages": [{"role": "user", "content": "&"}],
                }
            ],
        ]
    )
    @patch(
        "api.services.OpenAICacheService.openai_request",
        side_effect=mock_openai_request,
    )
    def test_cache_case(self, request_data, mock_openai_request):
        endpoint = "v1/chat/completions"
        self.exec(request_data, endpoint)
