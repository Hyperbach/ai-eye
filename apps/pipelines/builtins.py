import datetime
import inspect
import sys
from typing import Any, Callable, Dict

import pytz


# example of builtin function
def concat(arg1, arg2) -> str:
    return f"{arg1} {arg2}"


# example of builtin function
def now(timezone) -> str:
    tz = pytz.timezone(timezone)
    return str(datetime.datetime.now(tz=tz))


# example of builtin function
def identity(s: str) -> str:
    return s


def list_functions(mod):
    def is_module_function(mod, func):
        return inspect.isfunction(func) and inspect.getmodule(func) == mod

    return [
        func
        for func in mod.__dict__.values()
        if is_module_function(mod, func) and func.__name__ not in IGNORED_FUNCTION_NAMES
    ]


def dict_functions(mod):
    return {func.__name__: func for func in list_functions(mod)}


def get_builtin_function_names():
    return (
        (func.__name__, func.__name__) for func in list_functions(sys.modules[__name__])
    )


def call_builtin_function(name, **kwargs) -> Any:
    return BUILTIN_FUNCTIONS_DICT[name](**kwargs)


def get_arg_name_by_index(function_name, index):
    func = BUILTIN_FUNCTIONS_DICT[function_name]
    argspec = inspect.getfullargspec(func)
    return argspec.args[index]


def get_arity_of_function(func_name):
    func = BUILTIN_FUNCTIONS_DICT[func_name]
    return len(inspect.getfullargspec(func).args)


IGNORED_FUNCTION_NAMES = [
    "list_functions",
    "dict_functions",
    "get_builtin_function_names",
    "get_arity_of_function",
    "get_arg_name_by_index",
    "call_builtin_function",
]

BUILTIN_FUNCTIONS_DICT: Dict[str, Callable] = dict_functions(sys.modules[__name__])
