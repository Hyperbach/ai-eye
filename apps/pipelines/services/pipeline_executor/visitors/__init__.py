import abc
import logging
from typing import Any, Dict, List, Type

from django.contrib.auth.models import AbstractUser

import networkx as nx
from pipelines.models import BuiltinFunction, Prompt
from pipelines.services.exceptions import (
    InvalidArgumentsError,
    UnableToDetermineFunctionError,
)
from pipelines.services.pipeline_executor.calls import CallBuiltinFunction, CallPrompt
from pipelines.utils import find_first

logger = logging.getLogger("db")


class BaseVisitor(metaclass=abc.ABCMeta):
    def __init__(
            self, graph: nx.DiGraph, prompts: List[Prompt], builtins: List[BuiltinFunction]
    ):
        self.graph = graph
        self.prompts = prompts
        self.builtins = builtins

    def _create_call_func_by_name(self, name):
        if prompt_fn := find_first(lambda p: p.name == name, self.prompts):
            return CallPrompt(prompt_fn=prompt_fn)
        if builtin_fn := find_first(lambda b: b.name == name, self.builtins):
            return CallBuiltinFunction(builtin_fn=builtin_fn)

        return None

    @staticmethod
    def is_placeholder(target_fn):
        return target_fn is None

    def visit(self, node) -> Any:
        target_fn = self._create_call_func_by_name(node.name)
        if self.is_placeholder(target_fn):
            if not list(self.graph.predecessors(node)):
                raise UnableToDetermineFunctionError(fn_name=node.name)
            return self.visit_leaf(node)
        return self.visit_fn(node, target_fn)

    @abc.abstractmethod
    def visit_leaf(self, node) -> Any:
        pass

    @abc.abstractmethod
    def visit_fn(self, node, target_fn) -> Any:
        pass


class ArgumentsGathererVisitor(BaseVisitor):
    def visit_leaf(self, node) -> Any:
        return {node.name}

    def visit_fn(self, node, target_fn) -> Any:
        arg_names = set()

        for index, child in enumerate(self.graph.successors(node)):
            child_func = self._create_call_func_by_name(child.name)
            if self.is_placeholder(child_func):
                assign_arg_nodes = list(self.graph.successors(child))
                if len(assign_arg_nodes) > 0:
                    assert len(assign_arg_nodes) == 1
                    arg_names.update(self.visit(assign_arg_nodes[0]))
                else:
                    arg_names.update(self.visit_leaf(child))
            else:
                arg_names.update(self.visit_fn(child, child_func))

        return arg_names


class ExecutorVisitor(BaseVisitor):
    def __init__(
        self,
        graph: nx.DiGraph,
        prompts: List[Prompt],
        builtins: List[BuiltinFunction],
        openaikey: str,
        user_args: Dict[str, str],
        user: Type[AbstractUser],
    ):
        super().__init__(graph=graph, prompts=prompts, builtins=builtins)
        self.openaikey = openaikey
        self.user_args = user_args
        self.user = user

    def _find_arg_value(self, arg_name):
        arg_value = self.user_args.get(arg_name, None)
        if arg_value is None:
            error_msg = f"details: Argument named `{arg_name}` is not supplied."
            raise InvalidArgumentsError(error_msg)
        return arg_value

    def visit_leaf(self, node) -> Any:
        return self._find_arg_value(node.name)

    def visit_fn(self, node, target_fn) -> Any:
        kwargs = {}

        for index, child in enumerate(self.graph.successors(node)):
            child_func = self._create_call_func_by_name(child.name)
            arg_name = child.name

            assign_arg = False
            if self.is_placeholder(child_func):
                assign_arg_nodes = list(self.graph.successors(child))
                if assign_arg := len(assign_arg_nodes) > 0:
                    assert len(assign_arg_nodes) == 1
                    arg_value = self.visit(assign_arg_nodes[0])
                else:
                    arg_value = self.visit_leaf(child)
            else:
                arg_value = self.visit(child)

            if not assign_arg and isinstance(target_fn, CallBuiltinFunction):
                try:
                    arg_name = target_fn.get_arg_name_by_index(index)
                except IndexError as exc:
                    raise InvalidArgumentsError(f"Invalid arguments. Details {exc}")

            kwargs[arg_name] = arg_value

        fn_arity = target_fn.get_arity_of_function()
        fn_call_arity = len(kwargs)
        if fn_arity != fn_call_arity:
            error_msg = f"function expects: {fn_arity}, user provided {fn_call_arity}"
            raise InvalidArgumentsError(
                f"Invalid arguments amount specified. {error_msg}"
            )

        if isinstance(target_fn, CallPrompt):
            fn_arg_names = target_fn.get_arg_names()
            if len(fn_arg_names) == 1 and len(kwargs) == 1:
                fn_arg_name = fn_arg_names[0]
                if fn_arg_name not in kwargs:
                    kwargs_values = list(kwargs.values())
                    kwargs = {
                        fn_arg_name: kwargs_values[0],
                    }

            kwargs.update({"openaikey": self.openaikey, "user": self.user})
        elif isinstance(target_fn, CallBuiltinFunction):
            user_prompts = Prompt.objects.filter(owner=self.user)
            prompt_details = {prompt.name: prompt.description for prompt in user_prompts}
            kwargs.update({"openaikey": self.openaikey, "prompts": prompt_details})

        return target_fn(**kwargs)
