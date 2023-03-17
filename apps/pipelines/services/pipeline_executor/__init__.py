import logging
from typing import Dict

import networkx as nx
from dblogs.handlers import DatabaseLogHandler
from pipelines.models import BuiltinFunction, DAGEdge, DAGNode, Prompt
from pipelines.services.exceptions import (
    NoDAGNodesError,
    PipelineException,
    UnableToDetermineRootError,
)
from pipelines.services.pipeline_executor.visitors import (
    ArgumentsGathererVisitor,
    ExecutorVisitor,
)

logger = logging.getLogger("db")


class PipelineExecutor:
    def __init__(self, pipeline_source_id, user):
        self.pipeline_source_id = pipeline_source_id
        self.graph, self.prompts, self.builtins = self._build_graph()
        self.root = self._get_root(self.graph)
        self.user = user

    def _build_graph(self):
        dag_nodes = DAGNode.objects.select_related().filter(
            pipeline_source_id=self.pipeline_source_id
        )
        if not dag_nodes:
            error_msg = f"Unable to find DAG nodes for the pipeline with id {self.pipeline_source_id}."
            raise NoDAGNodesError(error_msg)

        dag_edges = DAGEdge.objects.select_related("from_node", "to_node").filter(
            from_node__in=dag_nodes
        )

        node_names = dag_nodes.values_list("name", flat=True)
        prompts = list(Prompt.objects.filter(name__in=node_names))
        builtins = list(BuiltinFunction.objects.filter(name__in=node_names))

        graph = nx.DiGraph()
        graph.add_nodes_from(dag_nodes)
        edges = [(edge.from_node, edge.to_node) for edge in dag_edges]
        graph.add_edges_from(edges)

        return graph, prompts, builtins

    def _get_root(self, graph):
        roots = [n for n, d in graph.in_degree() if d == 0]
        if len(roots) != 1:
            raise UnableToDetermineRootError(
                "The root node of the DAG cannot be determined."
            )
        return roots[0]

    def exec(self, user_args: Dict[str, str], openaikey: str):
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

        logger.info(
            msg=DatabaseLogHandler.Event.STARTED,
            extra={
                "meta_info": {
                    "user": self.user,
                    "pipeline_id": self.pipeline_source_id,
                    "openai_key": openaikey,
                    "parameters": user_args,
                }
            },
        )

        result = ""
        error = ""
        try:
            result = ExecutorVisitor(
                graph=self.graph,
                prompts=self.prompts,
                builtins=self.builtins,
                openaikey=openaikey,
                user_args=user_args,
            ).visit(node=self.root)
        except PipelineException as exc:
            error = str(exc)
            raise exc
        finally:
            logger.info(
                msg=DatabaseLogHandler.Event.COMPLETED,
                extra={
                    "meta_info": {
                        "event": DatabaseLogHandler.Event.COMPLETED,
                        "output": result,
                        "error": error,
                        "status": "success" if not error else "error",
                    }
                },
            )

        return result

    def get_arg_names(self):
        return ArgumentsGathererVisitor(
            graph=self.graph,
            prompts=self.prompts,
            builtins=self.builtins,
        ).visit(node=self.root)
