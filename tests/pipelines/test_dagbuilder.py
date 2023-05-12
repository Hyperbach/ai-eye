from django.test import TestCase

import lark.exceptions
from parameterized import param, parameterized
from pipelines.services.dag_builder import DAGBuilder, Edge, Node


class DAGBuilderTestCase(TestCase):
    def setUp(self) -> None:
        self.builder = DAGBuilder()

    def test_single_function_invocation(self):
        try:
            root = self.builder.build("foo()")
        except Exception as exc:
            self.fail(f"test_single_function_invocation raised an exception: {exc}")

        self.assertEqual(root.name, "foo")
        self.assertEqual(len(root.edges), 0)

    def test_multiple_function_invocations(self):
        try:
            root = self.builder.build("a(b(), c())")
        except Exception as exc:
            self.fail(f"test_multiple_function_invocations raised an exception: {exc}")

        self.assertEqual(root.name, "a")

        # Assert that there are 2 edges created for the root node
        self.assertEqual(len(root.edges), 2)

        # Assert that there is an edge from the root node to each argument node
        self.assertEqual(root.edges[0].source, root)
        self.assertEqual(root.edges[1].source, root)

        # Assert that each argument of the function call is a separate node
        node_b, node_c = root.edges[0].target, root.edges[1].target
        self.assertEqual(node_b.name, "b")
        self.assertEqual(node_c.name, "c")

        self.assertEqual(len(node_b.edges), 0)
        self.assertEqual(len(node_c.edges), 0)

    def test_function_invocations_with_named_arguments(self):
        try:
            root = self.builder.build("foo(a=a1, b=b2)")
        except Exception as exc:
            self.fail(
                f"test_function_invocations_with_named_arguments raised an exception: {exc}"
            )

        self.assertEqual(root.name, "foo")

        # Assert that there are 2 edges created for the root node
        self.assertEqual(len(root.edges), 2)

        # Assert that there is an edge from the root node to each argument node
        self.assertEqual(root.edges[0].source, root)
        self.assertEqual(root.edges[1].source, root)

        node_a, node_b = root.edges[0].target, root.edges[1].target
        self.assertEqual(node_a.name, "a")
        self.assertEqual(node_b.name, "b")

        self.assertEqual(len(node_a.edges), 1)
        self.assertEqual(len(node_b.edges), 1)

        node_a_edge = node_a.edges[0]
        node_b_edge = node_b.edges[0]

        self.assertEqual(node_a_edge.source, node_a)
        self.assertEqual(node_b_edge.source, node_b)
        self.assertEqual(node_a_edge.target.name, "a1")
        self.assertEqual(node_b_edge.target.name, "b2")

        self.assertEqual(len(node_a_edge.target.edges), 0)
        self.assertEqual(len(node_b_edge.target.edges), 0)

    def test_function_invocations_with_unnamed_arguments(self):
        try:
            root = self.builder.build("foo(a, b)")
        except Exception as exc:
            self.fail(
                f"test_function_invocations_with_unnamed_arguments raised an exception: {exc}"
            )

        self.assertEqual(root.name, "foo")

        # Assert that there are 2 edges created for the root node
        self.assertEqual(len(root.edges), 2)

        # Assert that there is an edge from the root node to each argument node
        self.assertEqual(root.edges[0].source, root)
        self.assertEqual(root.edges[1].source, root)

        node_a, node_b = root.edges[0].target, root.edges[1].target

        self.assertEqual(node_a.name, "a")
        self.assertEqual(node_b.name, "b")

        self.assertEqual(len(node_a.edges), 0)
        self.assertEqual(len(node_b.edges), 0)

    def test_add_edge_method(self):
        node1 = Node("node1")
        node2 = Node("node2")
        edge = Edge(node1, node2)

        self.assertEqual(len(node1.edges), 0)
        self.assertEqual(len(node2.edges), 0)

        node2.add_edge(edge)

        self.assertEqual(len(node1.edges), 0)
        self.assertEqual(len(node2.edges), 1)
        self.assertEqual(node2.edges[0].source, node1)

    def test_nested_function_invocations_with_arguments(self):
        try:
            root = self.builder.build("foo(a=bar(b=b1))")
        except Exception as exc:
            self.fail(
                f"test_nested_function_invocations_with_arguments raised an exception: {exc}"
            )

        self.assertEqual(root.name, "foo")

        # Assert that there is 1 edge created for the root node
        self.assertEqual(len(root.edges), 1)

        self.assertEqual(root.edges[0].source, root)
        a_node = root.edges[0].target
        self.assertEqual(a_node.name, "a")
        self.assertEqual(len(a_node.edges), 1)
        self.assertEqual(a_node.edges[0].source, a_node)
        self.assertEqual(a_node.edges[0].target.name, "bar")

        bar_node = a_node.edges[0].target
        self.assertEqual(len(bar_node.edges), 1)
        self.assertEqual(bar_node.edges[0].source, bar_node)
        self.assertEqual(bar_node.edges[0].target.name, "b")

        b_node = bar_node.edges[0].target
        self.assertEqual(len(b_node.edges), 1)
        self.assertEqual(b_node.edges[0].source, b_node)
        self.assertEqual(b_node.edges[0].target.name, "b1")

        b1_node = b_node.edges[0].target
        self.assertEqual(len(b1_node.edges), 0)

    @parameterized.expand(
        [
            param(""),
            param(" "),
            param("123"),
            param("x("),
            param("x)"),
            param("()"),
            param("(x)"),
            param("x(y"),
            param("x y"),
            param("x(123)"),
            param("x(y=123)"),
            param("x(123=z)"),
            param("x(y=123z)"),
            param("x(123y=z)"),
            param("x=123"),
            param("x"),
        ]
    )
    def test_invalid_inputs(self, input_str):
        with self.assertRaises(lark.exceptions.LarkError):
            _ = self.builder.build(input_str)
