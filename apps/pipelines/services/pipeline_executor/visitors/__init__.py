import abc
import logging
from typing import Any, Dict, List, Type

import networkx as nx
from django.contrib.auth.models import AbstractUser

from core.models import APIKey
from pipelines.models import BuiltinFunction, Prompt
from pipelines.services.exceptions import (
    InvalidArgumentsError,
    UnableToDetermineFunctionError,
)
from pipelines.services.functions_manager import FUNCTIONS_MANAGER
from pipelines.services.pipeline_executor.calls import CallBuiltinFunction, CallPrompt
from pipelines.utils import find_first, strip_json_response

logger = logging.getLogger("db")
console_logger = logging.getLogger("console")


class BaseVisitor(metaclass=abc.ABCMeta):
    def __init__(
            self, graph: nx.DiGraph, prompts: List[Prompt], builtins: List[BuiltinFunction]
    ):
        self.graph = graph
        self.prompts = prompts
        self.builtins = builtins

    def _create_call_func_by_name(self, name):
        if prompt_fn := find_first(lambda p: p.name == name, self.prompts):
            # use strict=True only when json=True (not implemented yet)
            return strip_json_response(CallPrompt(prompt_fn=prompt_fn), strict=False)
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
            apikey: APIKey,
            user_args: Dict[str, str],
            user: Type[AbstractUser],
    ):
        super().__init__(graph=graph, prompts=prompts, builtins=builtins)
        self.apikey = apikey
        self.user_args = user_args
        self.user = user

        # Initialize the global context
        user_prompts = Prompt.objects.filter(owner=self.user)
        prompt_details = {prompt.name: prompt.description for prompt in user_prompts}
        self.global_context = {
            "apikey": self.apikey,
            "prompts": prompt_details,
            "functions": FUNCTIONS_MANAGER.funcs,
        }

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
        output_var_name = kwargs.pop("set", None)

        # Decrease expected arity if 'set' is present. Why? Because 'set' is not a real argument. It's a
        # special keyword that is used to store the result of the function in the context.vars
        # Example: identity(x, set=var1)
        # In this case, the function 'identity' expects 1 argument, but the user provided 2 arguments: x and set=var1
        # Meaning that the function will be called with 1 argument: x.
        # And the result of the function will be stored in context.vars['var1']
        if output_var_name is not None:
            fn_call_arity -= 1  # Decrease expected arity if 'set' is present
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

            kwargs.update({"apikey": self.apikey, "user": self.user})
        elif isinstance(target_fn, CallBuiltinFunction):
            target_function = FUNCTIONS_MANAGER.get_function(target_fn.builtin_fn.name)
            if hasattr(target_function, "needs_context") and target_function.needs_context:
                setattr(target_function, "context", self.global_context)

        console_logger.info(f"Context before calling function: {self.global_context}")
        # Call the function
        result = target_fn(**kwargs)

        # Store the result in context.vars if 'set' parameter is specified
        if output_var_name:
            console_logger.info(f"Storing result in context.vars['{output_var_name}']")
            if 'vars' not in self.global_context:
                self.global_context['vars'] = {}
            self.global_context['vars'][output_var_name] = result

        console_logger.info(f"Context after calling function: {self.global_context}")

        return result
