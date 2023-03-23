from typing import Any
from unittest.mock import patch

from django.test import TestCase

import lark.exceptions
from parameterized import parameterized
from pipelines.models import BuiltinFunction, PipelineSource, Prompt
from pipelines.services.dag_builder import DAGBuilder
from pipelines.services.dag_saver import DAGSaver
from pipelines.services.exceptions import PipelineException
from pipelines.services.pipeline_executor import PipelineExecutor

from tests.factories import AiEyeAdminFactory, OpenAIKeyFactory


def mock_openai_request(openaikey: str, endpoint: str, parameters: dict[str, Any]):
    return f"OpenAI reply for {parameters['messages'][0]['content']}"


@patch(
    "pipelines.builtins.BUILTIN_FUNCTIONS_DICT",
    new={"builtin_concat": lambda x, y: f"{x} {y}", "builtin_identity": lambda s: s},
)
class PipelineExecutorTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        aieye_admin = AiEyeAdminFactory.create()
        cls.aieye_admin = aieye_admin
        Prompt.objects.create(
            name="prompt_a", body="this is {a_arg}", owner=aieye_admin
        )
        Prompt.objects.create(
            name="prompt_b", body="this is {b_arg}", owner=aieye_admin
        )

        BuiltinFunction.objects.create(name="builtin_concat")
        BuiltinFunction.objects.create(name="builtin_identity")

        cls.openaikey = OpenAIKeyFactory.create(owner=aieye_admin)

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
        "api.services.OpenAICacheService.openai_request",
        side_effect=mock_openai_request,
    )
    def test_positive_exec(self, test_data, mock_openai_request):
        input_str = test_data["input"]
        user_args = test_data["user_args"]
        expected = test_data["result"]

        try:
            pipeline_executor = self._create_pipeline_executor(input_str=input_str)
            result = pipeline_executor.exec(
                user_args=user_args, openaikey=self.openaikey.key
            )
        except Exception as exc:
            self.fail(f"test_positive_exec raised an exception: {exc}")

        self.assertEqual(result, expected)

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
            [
                {
                    "input": "foo",
                    "user_args": {"foo": "just placeholder"},
                    "exception": lark.exceptions.LarkError,
                }
            ],
        ]
    )
    @patch(
        "api.services.OpenAICacheService.openai_request",
        side_effect=mock_openai_request,
    )
    def test_negative_exec(self, test_data, mock_openai_request):
        input_str = test_data["input"]
        user_args = test_data["user_args"]
        expected_exception = test_data.get("exception", PipelineException)

        with self.assertRaises(expected_exception):
            pipeline_executor = self._create_pipeline_executor(input_str=input_str)
            _ = pipeline_executor.exec(
                user_args=user_args, openaikey=self.openaikey.key
            )

    @parameterized.expand(
        [
            [
                {
                    "input": "builtin_concat(prompt_a(a_arg), prompt_b(b_arg))",
                    "expected_user_args": {"a_arg", "b_arg"},
                }
            ],
            [
                {
                    "input": "builtin_concat(prompt_a(a_arg=a_arg_val), prompt_b(b_arg=b_arg_val))",
                    "expected_user_args": {"a_arg_val", "b_arg_val"},
                }
            ],
            [
                {
                    "input": "builtin_identity(s)",
                    "expected_user_args": {"s"},
                }
            ],
            [
                {
                    "input": "builtin_identity(s=x_arg)",
                    "expected_user_args": {"x_arg"},
                }
            ],
            [
                {
                    "input": "builtin_identity(whatever_named_arg)",
                    "expected_user_args": {"whatever_named_arg"},
                }
            ],
            [
                {
                    "input": "prompt_a(a_arg)",
                    "expected_user_args": {"a_arg"},
                }
            ],
            [
                {
                    "input": "prompt_a(a_arg=a_arg_val)",
                    "expected_user_args": {"a_arg_val"},
                }
            ],
        ]
    )
    @patch(
        "api.services.OpenAICacheService.openai_request",
        side_effect=mock_openai_request,
    )
    def test_exec_arg_names_only(self, test_data, mock_openai_request):
        input_str = test_data["input"]
        expected_user_args = test_data["expected_user_args"]

        try:
            pipeline_executor = self._create_pipeline_executor(input_str=input_str)
            result_user_args = pipeline_executor.get_arg_names()
        except Exception as exc:
            self.fail(f"test_exec_arg_names_only raised an exception: {exc}")

        self.assertCountEqual(expected_user_args, result_user_args)

    def _create_pipeline_executor(self, input_str):
        pipeline = PipelineSource.objects.create(
            name="test_pipeline", body=input_str, owner=self.aieye_admin
        )
        dag_root = DAGBuilder().build(input_str)
        dag_saver = DAGSaver(dag_root)
        dag_saver.save(pipeline)
        return PipelineExecutor(pipeline_source_id=pipeline.id, user=self.aieye_admin)
