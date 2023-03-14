import abc
import logging
from typing import Any, Dict, List

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
        logger.debug(
            msg="BaseVisitor method _create_call_func_by_name called",
            extra={"meta_info": f"name: {name}"},
        )

        if prompt_fn := find_first(lambda p: p.name == name, self.prompts):
            logger.debug(
                msg="BaseVisitor method _create_call_func_by_name found a prompt"
            )
            return CallPrompt(prompt_fn=prompt_fn)
        if builtin_fn := find_first(lambda b: b.name == name, self.builtins):
            logger.debug(
                msg="BaseVisitor method _create_call_func_by_name found a builtin_fn"
            )
            return CallBuiltinFunction(builtin_fn=builtin_fn)

        logger.debug(
            msg="BaseVisitor method _create_call_func_by_name did not find neither a prompt nor a builtin_fn"
        )
        return None

    @staticmethod
    def is_placeholder(target_fn):
        return target_fn is None

    def visit(self, node) -> Any:
        logger.debug(
            msg="BaseVisitor method visit called",
            extra={"meta_info": f"node.name: {node.name}"},
        )
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
        logger.debug(
            msg="ArgumentsGathererVisitor method visit_fn called",
            extra={"meta_info": f"node.name: {node.name}, target_fn: {target_fn}"},
        )

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

        arg_names_as_str = ", ".join(arg_names)
        logger.debug(
            msg="ArgumentsGathererVisitor method visit_fn call result",
            extra={"meta_info": f"arg_names: {arg_names_as_str}"},
        )

        return arg_names


class ExecutorVisitor(BaseVisitor):
    def __init__(
        self,
        graph: nx.DiGraph,
        prompts: List[Prompt],
        builtins: List[BuiltinFunction],
        openaikey: str,
        user_args: Dict[str, str],
    ):
        super().__init__(graph=graph, prompts=prompts, builtins=builtins)
        self.openaikey = openaikey
        self.user_args = user_args

    def _find_arg_value(self, arg_name):
        arg_value = self.user_args.get(arg_name, None)
        if arg_value is None:
            error_msg = f"details: Argument named `{arg_name}` is not supplied."
            logger.error(
                msg="ExecutorVisitor method _find_arg_value got an error",
                extra={"meta_info": error_msg},
            )
            raise InvalidArgumentsError(error_msg)
        return arg_value

    def visit_leaf(self, node) -> Any:
        return self._find_arg_value(node.name)

    def visit_fn(self, node, target_fn) -> Any:
        logger.debug(
            msg="ExecutorVisitor method visit_fn called",
            extra={"meta_info": f"node: {node.name}, target_fn: {target_fn}"},
        )

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
                    logger.error(
                        msg="ExecutorVisitor method visit_fn got an error. Invalid arguments.",
                        extra={"meta_info": f"details: {exc}"},
                    )

                    raise InvalidArgumentsError(f"Invalid arguments. Details {exc}")

            kwargs[arg_name] = arg_value

        fn_arity = target_fn.get_arity_of_function()
        fn_call_arity = len(kwargs)
        if fn_arity != fn_call_arity:
            error_msg = f"function expects: {fn_arity}, user provided {fn_call_arity}"
            logger.error(
                msg="ExecutorVisitor method visit_fn got an error.",
                extra={"meta_info": error_msg},
            )

            raise InvalidArgumentsError(
                f"Invalid arguments amount specified. {error_msg}"
            )

        if isinstance(target_fn, CallPrompt):
            kwargs.update({"openaikey": self.openaikey})

        logger.debug(
            msg="ExecutorVisitor method visit_fn is about to invoke a target_fn",
            extra={"meta_info": f"target_fn: {target_fn}"},
        )
        return target_fn(**kwargs)
