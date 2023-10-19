import glob
import importlib
import inspect
import os
from typing import Any

from pipelines.services.exceptions import LoadModuleError, UserDefinedFunctionsError


class FunctionsManager:
    FUNCS_PACKAGE_NAME = "funcs"
    USER_DEFINED_MODULES_NAME_PATTERN = "custom_*.py"
    IGNORED_BUILTIN_FUNCTIONS = ["get_context", "type_inference_decorator"]

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.funcs = {}
        self.builtin_func_names = []
        self.force_reload()

    def force_reload(self):
        self._load_functions()

    def get_function(self, name):
        return self.funcs.get(name)

    def get_func_names(self):
        return list(self.funcs.keys())

    def call_builtin_function(self, name, **kwargs) -> Any:
        return self.funcs[name](**kwargs)

    def get_arg_name_by_index(self, name, index):
        func = self.funcs[name]
        argspec = inspect.getfullargspec(func)
        return argspec.args[index]

    def get_arity_of_function(self, name):
        func = self.funcs[name]
        return len(inspect.getfullargspec(func).args)

    def is_builtin_function(self, name):
        return name in self.builtin_func_names

    def _load_functions(self):
        # load builtin functions which should be kept in git
        builtins_module = self._import_module(f"{self.FUNCS_PACKAGE_NAME}.builtins")
        self.funcs = self._get_module_functions(builtins_module)
        self.builtin_func_names = self.get_func_names()

        # load user-defined functions which should not be kept in git and are optional
        user_module_files = glob.glob(
            os.path.join(
                self.FUNCS_PACKAGE_NAME.replace(".", os.path.sep),
                self.USER_DEFINED_MODULES_NAME_PATTERN,
            )
        )
        for user_module in user_module_files:
            module_name = self._get_module_name(user_module)
            custom_module = self._import_module(module_name)
            custom_funcs = self._get_module_functions(custom_module)
            intersecting_keys = self.funcs.keys() & custom_funcs.keys()
            if intersecting_keys:
                raise UserDefinedFunctionsError(
                    f"Unable to load user-defined functions from module {module_name}. "
                    f"The following function names are already defined by the built-in module or user-defined ones: {intersecting_keys}"
                )
            self.funcs.update(custom_funcs)

    def _get_module_name(self, file_path):
        return os.path.splitext(file_path)[0].replace("/", ".")

    def _import_module(self, module_name):
        try:
            module = importlib.import_module(module_name)
        except (ModuleNotFoundError, ImportError) as e:
            raise LoadModuleError(f"Unable to import module {module_name}: {e}")
        else:
            return module

    def _get_module_functions(self, mod):
        def is_module_function(mod, func):
            return inspect.isfunction(func) and inspect.getmodule(func) == mod

        return {
            func.__name__: func
            for func in mod.__dict__.values()
            if is_module_function(mod, func) and func.__name__ not in self.IGNORED_BUILTIN_FUNCTIONS
        }


FUNCTIONS_MANAGER = FunctionsManager()
