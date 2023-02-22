import inspect
import sys


def builtin_fn1(arg1, arg2):
    return "For only {arg1} dollars you'll get {arg2} goods".format(
        arg1=arg1, arg2=arg2
    )


def builtin_fn2(arg):
    return f"{arg} B"


def builtin_fn3(arg1, arg2):
    return "C" * arg1 + f" {arg2}"


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


def get_list_of_builtin_function_names():
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
    "get_list_of_builtin_function_names",
    "get_arity_of_func",
]

BUILTIN_FUNCTIONS_DICT = dict_functions(sys.modules[__name__])
