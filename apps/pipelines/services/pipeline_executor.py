import re

import networkx as nx
from api.services import openai_request
from pipelines.builtins import (
    call_builtin_function,
    get_arg_name_by_index,
    get_arity_of_function,
)
from pipelines.models import BuiltinFunction, DAGEdge, DAGNode, Prompt
from pipelines.services.exceptions import (
    CallBuiltinFunctionError,
    CallPromptError,
    InvalidArgumentsError,
    NoDAGNodesError,
    UnableToDetermineRootError,
)
from pipelines.utils import find_first


class CallBuiltinFunction:
    def __init__(self, builtin_fn):
        self.builtin_fn = builtin_fn

    def __str__(self):
        return self.builtin_fn.name

    def get_arity_of_function(self):
        return get_arity_of_function(self.builtin_fn.name)

    def __call__(self, **kwargs):
        try:
            return call_builtin_function(self.builtin_fn.name, **kwargs)
        except Exception as exc:
            raise CallBuiltinFunctionError(
                f"An error occurred while calling the function '{self.builtin_fn.name}'. Details: {exc}"
            )

    def get_arg_name_by_index(self, index):
        return get_arg_name_by_index(self.builtin_fn.name, index)


class CallPrompt:
    ARGS_PATTERN_RX = re.compile(r"{[a-zA-Z][a-zA-Z_0-9]*}")

    def __init__(self, prompt_fn, openaikey):
        self.prompt_fn = prompt_fn
        self.openaikey = openaikey
        self.endpoint = "v1/completions"
        self.model = "text-davinci-003"

    def __str__(self):
        return self.prompt_fn.name

    def get_arity_of_function(self):
        arg_names = self.ARGS_PATTERN_RX.findall(self.prompt_fn.body)
        return len(set(arg_names))

    def __call__(self, **kwargs):
        body = self.prompt_fn.body

        try:
            prompt = body.format(**kwargs)
            return openai_request(
                openaikey=self.openaikey,
                endpoint=self.endpoint,
                parameters={"model": self.model, "prompt": prompt},
            )
        except Exception as exc:
            raise CallPromptError(
                f"An error occurred while calling the function '{self.prompt_fn.name}'. Details: {exc}"
            )


class PipelineExecutor:
    def __init__(self, pipeline_source_id, user_args, openaikey):
        self.pipeline_source_id = pipeline_source_id
        self.user_args = user_args
        self.openaikey = openaikey

        self.graph, self.prompts, self.builtins = self.build_graph()
        self.root = self.get_root(self.graph)

    def build_graph(self):
        dag_nodes = DAGNode.objects.filter(
            pipeline_source_id=self.pipeline_source_id
        ).all()
        if not dag_nodes:
            raise NoDAGNodesError(
                f"Unable to find DAG nodes belonging to the pipeline with id {self.pipeline_source_id}."
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
        if len(roots) != 1:
            raise UnableToDetermineRootError(
                "The root node of the DAG cannot be determined."
            )
        return roots[0]

    def find_func_by_name(self, name):
        if prompt_fn := find_first(lambda p: p.name == name, self.prompts):
            return CallPrompt(prompt_fn=prompt_fn, openaikey=self.openaikey)
        if builtin_fn := find_first(lambda p: p.name == name, self.builtins):
            return CallBuiltinFunction(builtin_fn)
        return None

    def find_arg_value(self, arg_name):
        arg_value = self.user_args.get(arg_name, None)
        if arg_value is None:
            raise InvalidArgumentsError(f"Argument named `{arg_name}` is not supplied.")
        return arg_value

    @staticmethod
    def is_placeholder(target_fn):
        return target_fn is None

    def _exec(self, node):
        target_fn = self.find_func_by_name(node.name)
        if self.is_placeholder(target_fn):
            return self.find_arg_value(node.name)

        kwargs = {}

        for index, child in enumerate(self.graph.successors(node)):
            child_func = self.find_func_by_name(child.name)
            arg_name = child.name

            assign_arg = False
            if self.is_placeholder(child_func):
                assign_arg_nodes = list(self.graph.successors(child))
                if assign_arg := len(assign_arg_nodes) > 0:
                    assert len(assign_arg_nodes) == 1
                    arg_value = self._exec(assign_arg_nodes[0])
                else:
                    arg_value = self.find_arg_value(arg_name)
            else:
                arg_value = self._exec(child)

            if not assign_arg and isinstance(target_fn, CallBuiltinFunction):
                try:
                    arg_name = target_fn.get_arg_name_by_index(index)
                except IndexError as exc:
                    raise InvalidArgumentsError(f"Invalid arguments. Details {exc}")

            kwargs[arg_name] = arg_value

        fn_arity = target_fn.get_arity_of_function()
        fn_call_arity = len(kwargs)
        if fn_arity != fn_call_arity:
            raise InvalidArgumentsError(
                f"Invalid arguments amount specified. "
                f"Function expects {fn_arity}, "
                f"but user provided {fn_call_arity}."
            )

        return target_fn(**kwargs)

    def exec(self):
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
        return self._exec(self.root)
