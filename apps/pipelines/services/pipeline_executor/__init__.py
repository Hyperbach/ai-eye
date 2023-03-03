import networkx as nx
from pipelines.models import BuiltinFunction, DAGEdge, DAGNode, Prompt
from pipelines.services.exceptions import NoDAGNodesError, UnableToDetermineRootError
from pipelines.services.pipeline_executor.visitors import (
    ArgumentsGathererVisitor,
    ExecutorVisitor,
)


class PipelineExecutor:
    def __init__(self, pipeline_source_id):
        self.pipeline_source_id = pipeline_source_id
        self.user_args = {}

        self.graph, self.prompts, self.builtins = self._build_graph()
        self.root = self._get_root(self.graph)

    def _build_graph(self):
        dag_nodes = DAGNode.objects.filter(
            pipeline_source_id=self.pipeline_source_id
        ).all()
        if not dag_nodes:
            raise NoDAGNodesError(
                f"Unable to find DAG nodes for the pipeline with id {self.pipeline_source_id}."
            )

        dag_edges = DAGEdge.objects.filter(from_node__in=dag_nodes).all()

        node_names = [n.name for n in dag_nodes]
        prompts = Prompt.objects.filter(name__in=node_names).all()
        builtins = BuiltinFunction.objects.filter(name__in=node_names).all()

        graph = nx.DiGraph()
        for node in dag_nodes:
            graph.add_node(node)
        for edge in dag_edges:
            graph.add_edge(edge.from_node, edge.to_node)

        return graph, prompts, builtins

    def _get_root(self, graph):
        roots = [n for n, d in graph.in_degree() if d == 0]
        if len(roots) != 1:
            raise UnableToDetermineRootError(
                "The root node of the DAG cannot be determined."
            )
        return roots[0]

    def exec(self, user_args, openaikey):
        """
        builtins:
        --
        identity(s)
        identity(s=xxx)
        identity(testme) <-- works also

        prompts:
        --
        some_prompt_with_one_argument(xyz)
        some_prompt_with_one_argument(xyz=r)
        some_prompt_with_one_argument(testme) <-- won't work
        """
        return ExecutorVisitor(
            graph=self.graph,
            prompts=self.prompts,
            builtins=self.builtins,
            openaikey=openaikey,
            user_args=user_args,
        ).visit(node=self.root)

    def get_arg_names(self):
        return ArgumentsGathererVisitor(
            graph=self.graph,
            prompts=self.prompts,
            builtins=self.builtins,
        ).visit(node=self.root)
