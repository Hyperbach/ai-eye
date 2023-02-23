import re

import networkx as nx
from pipelines.builtins import get_arity_of_function, invoke_builtin_function
from pipelines.models import BuiltinFunction, DAGEdge, DAGNode, Prompt
from pipelines.services.exceptions import (
    CallBuiltinFunctionError,
    CallPromptError,
    InvalidArgumentsError,
    NoDAGNodesError,
    UnableToDetermineRootError,
)


class CallBuiltinFunction:
    def __init__(self, builtin_fn):
        self.builtin_fn = builtin_fn

    def __str__(self):
        return self.builtin_fn.name

    def get_arity_of_function(self):
        return get_arity_of_function(self.builtin_fn.name)

    def __call__(self, *args, **kwargs):
        try:
            return invoke_builtin_function(self.builtin_fn.name, *args)
        except Exception as exc:
            raise CallBuiltinFunctionError(
                f"An error occurred while calling the function '{self.builtin_fn.name}'. Details: {exc}"
            )


class CallPrompt:
    ARGS_PATTERN_RX = re.compile(r"{[a-zA-Z][a-zA-Z_0-9]*}")

    def __init__(self, prompt):
        self.prompt = prompt

    def __str__(self):
        return self.prompt.name

    def get_arity_of_function(self):
        arg_names = self.ARGS_PATTERN_RX.findall(self.prompt.body)
        return len(set(arg_names))

    def __call__(self, *args, **kwargs):
        body = self.prompt.body
        try:
            result = body.format(**kwargs)
            # TODO: Openai API
            return result
        except Exception as exc:
            raise CallPromptError(
                f"An error occurred while calling the function '{self.prompt.name}'. Details: {exc}"
            )


class PipelineExecutor:
    def __init__(self, pipeline_source_id, args, openaikey):
        self.pipeline_source_id = pipeline_source_id
        self.args = args
        self.openaikey = openaikey

        self.graph, self.prompts, self.builtins = self.build_graph()
        self.root = self.get_root(self.graph)

    def build_graph(self):
        dag_nodes = DAGNode.objects.filter(
            pipeline_source_id=self.pipeline_source_id
        ).all()
        if not dag_nodes:
            raise NoDAGNodesError(
                f"Unable to find DAG nodes belonging to the pipeline "
                f"with id {self.pipeline_source_id}."
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

    @staticmethod
    def get_root(graph):
        roots = [n for n, d in graph.in_degree() if d == 0]
        if not roots or len(roots) > 1:
            raise UnableToDetermineRootError("Unable to determine root node of a DAG.")
        return roots[0]

    def find_func_by_name(self, name):
        def find_first(src_coll):
            return next(filter(lambda p: p.name == name, src_coll), None)

        if prompt_fn := find_first(self.prompts):
            return CallPrompt(prompt_fn)
        if builtin_fn := find_first(self.builtins):
            return CallBuiltinFunction(builtin_fn)
        return None

    def find_arg_value(self, arg_name):
        arg_value = self.args.get(arg_name, None)
        if arg_value is None:
            raise InvalidArgumentsError(f"Argument named `{arg_name}` is not supplied.")
        return arg_value

    @staticmethod
    def is_placeholder(target_fn):
        return target_fn is None

    def _exec(self, node):
        target_fn = self.find_func_by_name(node.name)
        if self.is_placeholder(target_fn):
            arg_value = self.find_arg_value(node.name)
            return arg_value

        args = []
        kwargs = {}

        for child in self.graph.successors(node):
            child_func = self.find_func_by_name(child.name)
            arg_name = child.name
            if self.is_placeholder(child_func):
                arg_value = self.find_arg_value(arg_name)
            else:
                arg_value = self._exec(child)

            if isinstance(target_fn, CallPrompt):
                kwargs[arg_name] = arg_value
            else:
                args.append(arg_value)

        fn_arity = target_fn.get_arity_of_function()
        call_arity = (
            len(args) if isinstance(target_fn, CallBuiltinFunction) else len(kwargs)
        )
        if fn_arity != call_arity:
            raise InvalidArgumentsError(
                f"Invalid arguments amount specified. "
                f"Function expects {fn_arity}, "
                f"but user provided {call_arity}."
            )

        return target_fn(args, **kwargs)

    def exec(self):
        return self._exec(self.root)
