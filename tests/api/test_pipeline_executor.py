from http import HTTPStatus
from typing import Any, Dict
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from api.models import User
from core.models import PublicToken
from parameterized import parameterized
from pipelines.models import BuiltinFunction, PipelineSource, Prompt
from pipelines.services.dag_builder import DAGBuilder
from pipelines.services.dag_saver import DAGSaver
from rest_framework.test import APIClient

from tests import AIEYE_ADMIN_PASSWORD
from tests.factories import (
    AiEyeAdminFactory,
    AiEyeUserFactory,
    OpenAIKeyFactory,
    PublicTokenFactory,
)


def mock_openai_request(openaikey: str, endpoint: str, parameters: Dict[str, Any]):
    return f"OpenAI reply for {parameters['messages'][0]['content']}"


@patch(
    "pipelines.builtins.BUILTIN_FUNCTIONS_DICT",
    new={"builtin_concat": lambda x, y: f"{x} {y}", "builtin_identity": lambda s: s},
)
class PipelineExecutorAPITestCase(TestCase):
    aieye_admin: User = None
    openaikey = None
    aieye_user = None
    publictoken: PublicToken = None

    @classmethod
    def setUpTestData(cls):
        aieye_admin = AiEyeAdminFactory.create()
        cls.aieye_admin = aieye_admin
        openaikey = OpenAIKeyFactory.create(owner=aieye_admin)
        cls.openaikey = openaikey
        aieye_user = AiEyeUserFactory.create()
        cls.aieye_user = aieye_user
        cls.publictoken = PublicTokenFactory.create(
            user=aieye_user, openaikey=openaikey
        )

        Prompt.objects.create(
            name="prompt_a", body="this is {a_arg}", owner=aieye_admin
        )
        Prompt.objects.create(
            name="prompt_b", body="this is {b_arg}", owner=aieye_admin
        )

        BuiltinFunction.objects.create(name="builtin_concat")
        BuiltinFunction.objects.create(name="builtin_identity")

        cls.pipeline_api_url = reverse("api:pipeline-list")
        cls.pipeline_retrieve_args_api_url = reverse("api:pipeline_args-list")

    def setUp(self) -> None:
        self.token_auth_client = APIClient()
        self.token_auth_client.credentials(
            HTTP_AUTHORIZATION="Bearer " + self.publictoken.key
        )

        self.session_auth_client = APIClient(enforce_csrf_checks=False)
        self.session_auth_client.login(
            email=self.aieye_admin.email, password=AIEYE_ADMIN_PASSWORD
        )

    def create_pipeline(self, input_str):
        pipeline = PipelineSource.objects.create(body=input_str, owner=self.aieye_admin)
        dag_root = DAGBuilder().build(input_str)
        dag_saver = DAGSaver(dag_root)
        dag_saver.save(pipeline)
        return pipeline

    def invoke_api(self, client, request_data):
        return client.post(self.pipeline_api_url, data=request_data, format="json")

    @parameterized.expand(
        [
            [
                {
                    "input": "builtin_concat(prompt_a(a_arg), prompt_b(b_arg))",
                    "user_args": {"a_arg": "aaa", "b_arg": "bbb"},
                    "result": "OpenAI reply for this is aaa OpenAI reply for this is bbb",
                }
            ],
            [
                {
                    "input": "builtin_concat(prompt_a(a_arg=a_arg_val), prompt_b(b_arg=b_arg_val))",
                    "user_args": {"a_arg_val": "aaa", "b_arg_val": "bbb"},
                    "result": "OpenAI reply for this is aaa OpenAI reply for this is bbb",
                }
            ],
            [
                {
                    "input": "builtin_identity(s)",
                    "user_args": {"s": "abc"},
                    "result": "abc",
                }
            ],
            [
                {
                    "input": "builtin_identity(s=x_arg)",
                    "user_args": {"x_arg": "abc"},
                    "result": "abc",
                }
            ],
            [
                {
                    "input": "builtin_identity(whatever_named_arg)",
                    "user_args": {"whatever_named_arg": "abc"},
                    "result": "abc",
                }
            ],
            [
                {
                    "input": "prompt_a(a_arg)",
                    "user_args": {"a_arg": "aaa"},
                    "result": "OpenAI reply for this is aaa",
                }
            ],
            [
                {
                    "input": "prompt_a(a_arg=a_arg_val)",
                    "user_args": {"a_arg_val": "aaa"},
                    "result": "OpenAI reply for this is aaa",
                }
            ],
        ]
    )
    @patch(
        "pipelines.services.pipeline_executor.calls.openai_request",
        side_effect=mock_openai_request,
    )
    def test_pipeline_positive_exec(self, test_data, mock_openai_request):
        input_str = test_data["input"]
        user_args = test_data["user_args"]
        expected = test_data["result"]

        pipeline = self.create_pipeline(input_str=input_str)

        for client in [self.token_auth_client, self.session_auth_client]:
            request_data = {
                "pipeline_id": pipeline.id,
                "args": user_args,
            }

            if client is self.session_auth_client:
                request_data.update({"openaikey_id": self.openaikey.id})

            response = self.invoke_api(client=client, request_data=request_data)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertEquals(response.data, {"success": True, "response": expected})

    @parameterized.expand(
        [
            [
                {
                    "input": "prompt_a(whatever_named_arg)",
                    "user_args": {"whatever_named_arg": "a"},
                }
            ],
            [{"input": "prompt_a()", "user_args": {}}],
            [{"input": "prompt_a(x, y)", "user_args": {}}],
            [{"input": "non_existing_prompt_or_builtin_fn()", "user_args": {}}],
            [{"input": "prompt_a(a_arg=prompt_a)", "user_args": {"prompt_a": "ABC"}}],
            [{"input": "prompt_a(prompt_a)", "user_args": {}}],
            [{"input": "builtin_concat()", "user_args": {}}],
            [
                {
                    "input": "builtin_concat(a, b, c)",
                    "user_args": {"a": "1", "b": "2", "c": "3"},
                }
            ],
        ]
    )
    @patch(
        "pipelines.services.pipeline_executor.calls.openai_request",
        side_effect=mock_openai_request,
    )
    def test_pipeline_negative_exec(self, test_data, mock_openai_request):
        input_str = test_data["input"]
        user_args = test_data["user_args"]

        pipeline = self.create_pipeline(input_str=input_str)

        for client in [self.token_auth_client, self.session_auth_client]:
            request_data = {
                "pipeline_id": pipeline.id,
                "args": user_args,
            }

            if client is self.session_auth_client:
                request_data.update({"openaikey_id": self.openaikey.id})

            response = self.invoke_api(client, request_data)
            self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    @parameterized.expand(
        [
            [
                {
                    "input": "builtin_concat(prompt_a(a_arg), prompt_b(b_arg))",
                    "expected_user_args": {"a_arg", "b_arg"},
                }
            ],
        ]
    )
    @patch(
        "pipelines.services.pipeline_executor.calls.openai_request",
        side_effect=mock_openai_request,
    )
    def test_exec_arg_names_only(self, test_data, mock_openai_request):
        input_str = test_data["input"]
        expected_user_args = test_data["expected_user_args"]

        pipeline = self.create_pipeline(input_str=input_str)
        request_data = {"pipeline_id": pipeline.id}

        response = self.session_auth_client.get(
            self.pipeline_retrieve_args_api_url, data=request_data, format="json"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEquals(
            response.data, {"success": True, "response": expected_user_args}
        )
