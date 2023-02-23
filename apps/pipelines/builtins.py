import datetime
import inspect
import sys

import pytz


# example of builtin function
def concat(arg1, arg2):
    return f"{arg1} {arg2}"


# example of builtin function
def now(timezone):
    tz = pytz.timezone(timezone)
    return str(datetime.datetime.now(tz=tz))


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


def invoke_builtin_function(name, args):
    return BUILTIN_FUNCTIONS_DICT[name](*args)


def get_arity_of_function(func_name):
    func = BUILTIN_FUNCTIONS_DICT[func_name]
    return len(inspect.getfullargspec(func).args)


IGNORED_FUNCTION_NAMES = [
    "list_functions",
    "dict_functions",
    "invoke_builtin_function",
    "get_builtin_function_names",
    "get_arity_of_function",
]

BUILTIN_FUNCTIONS_DICT = dict_functions(sys.modules[__name__])
