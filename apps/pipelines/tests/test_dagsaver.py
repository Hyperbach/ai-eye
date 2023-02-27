from django.test import TestCase

from pipelines.choices import TypesOfDAGNodes
from pipelines.models import BuiltinFunction, DAGEdge, DAGNode, PipelineSource, Prompt
from pipelines.services.dag_builder import DAGBuilder
from pipelines.services.dag_saver import DAGSaver

from tests.factories import AiEyeAdminFactory


class DAGSaverTestCase(TestCase):
    def setUp(self):
        self.aieye_admin = AiEyeAdminFactory.create()
        Prompt.objects.create(name="prompt_a", owner=self.aieye_admin)
        Prompt.objects.create(name="prompt_b", owner=self.aieye_admin)

        BuiltinFunction.objects.create(name="builtin_a")

        self.input_str = "builtin_a(prompt_a, prompt_b)"
        self.pipeline = PipelineSource.objects.create(body=self.input_str)

        self.dag_root = DAGBuilder().build(self.input_str)
        self.dag_saver = DAGSaver(self.dag_root)
        self.dag_saver.save(self.pipeline)

    def test_traverse_root(self):
        nodes, edges = self.dag_saver.traverse_root(self.dag_root)
        self.assertEqual(len(nodes), 3)
        self.assertEqual(len(edges), 2)

    def test_get_dag_node_type(self):
        node_type = self.dag_saver.get_dag_node_type("prompt_a")
        self.assertEqual(node_type, TypesOfDAGNodes.PROMPT)

        node_type = self.dag_saver.get_dag_node_type("builtin_a")
        self.assertEqual(node_type, TypesOfDAGNodes.BUILTIN_FUNCTION)

        node_type = self.dag_saver.get_dag_node_type("test_placeholder")
        self.assertEqual(node_type, TypesOfDAGNodes.PLACEHOLDER)

    def test_create_dag_nodes(self):
        nodes = DAGNode.objects.all()
        self.assertEqual(len(nodes), 3)

        node_names = [node.name for node in nodes]
        self.assertCountEqual(node_names, ["prompt_a", "prompt_b", "builtin_a"])

    def test_create_dag_edges(self):
        edges = DAGEdge.objects.all()
        self.assertEqual(len(edges), 2)

        source_names = [edge.from_node.name for edge in edges]
        self.assertCountEqual(source_names, ["builtin_a", "builtin_a"])

        target_names = [edge.to_node.name for edge in edges]
        self.assertCountEqual(target_names, ["prompt_a", "prompt_b"])
