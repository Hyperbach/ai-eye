from typing import Any
from unittest.mock import patch

from django.test import TestCase

from parameterized import parameterized
from pipelines.models import BuiltinFunction, PipelineSource, Prompt
from pipelines.services.dag_builder import DAGBuilder
from pipelines.services.dag_saver import DAGSaver
from pipelines.services.pipeline_executor import PipelineExecutor

from tests.factories import AiEyeAdminFactory


def openai_request_mock(openaikey: str, endpoint: str, parameters: dict[str, Any]):
    return f"OpenAI reply for {parameters['prompt']}"


@patch(
    "pipelines.builtins.BUILTIN_FUNCTIONS_DICT",
    new={"builtin_concat": lambda x, y: f"{x} {y}", "builtin_identity": lambda s: s},
)
class DAGSaverTestCase(TestCase):
    def setUp(self):
        aieye_admin = AiEyeAdminFactory.create()
        Prompt.objects.create(
            name="prompt_a", body="this is {a_arg}", owner=aieye_admin
        )
        Prompt.objects.create(
            name="prompt_b", body="this is {b_arg}", owner=aieye_admin
        )

        BuiltinFunction.objects.create(name="builtin_concat")
        BuiltinFunction.objects.create(name="builtin_identity")

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
            [
                {
                    "input": "foo",
                    "user_args": {"foo": "just placeholder"},
                    "result": "just placeholder",
                }
            ],
        ]
    )
    @patch(
        "pipelines.services.pipeline_executor.openai_request",
        side_effect=openai_request_mock,
    )
    def test_positive_exec(self, test_data, mock_openai_request):
        input_str = test_data["input"]
        user_args = test_data["user_args"]
        expected = test_data["result"]

        try:
            pipeline_executor = self._create_pipeline_executor(input_str=input_str)
            result = pipeline_executor.exec(user_args=user_args)
            self.assertEqual(result, expected)
        except Exception as exc:
            self.fail(f"test_exec raised an exception : {exc}")

    @staticmethod
    def _create_pipeline_executor(input_str):
        pipeline = PipelineSource.objects.create(body=input_str)
        dag_root = DAGBuilder().build(input_str)
        dag_saver = DAGSaver(dag_root)
        dag_saver.save(pipeline)

        return PipelineExecutor(pipeline_source_id=pipeline.id, openaikey="")
