import copy
import glob
import importlib
import inspect
from typing import Any

from pipelines.services.exceptions import LoadModuleError, UserDefinedFunctionsError


class FunctionsManager:
    FUNCS_PACKAGE_NAME = "funcs"
    USER_DEFINED_MODULES_NAME_PATTERN = "custom_*.py"
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.funcs = {}
            cls.__instance.builtin_funcs = {}
            cls.__instance.force_reload()

        return cls.__instance

    def force_reload(self):
        self._load_functions()

    def get_func_names(self):
        return self.funcs.keys()

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
        return name in self.builtin_funcs

    def _load_functions(self):
        # load builtin functions which should be kept in git
        builtins_module = self._import_module(f"{self.FUNCS_PACKAGE_NAME}.builtins")
        self.builtin_funcs = self._dict_functions(builtins_module)
        self.funcs = copy.copy(self.builtin_funcs)

        # load user-defined functions which should not be kept in git and are optional
        custom_module_names = glob.glob(
            f"{self.FUNCS_PACKAGE_NAME}/{self.USER_DEFINED_MODULES_NAME_PATTERN}"
        )
        for module_filename in custom_module_names:
            module_name = module_filename.split(".")[0].replace("/", ".")
            custom_module = self._import_module(module_name)
            custom_funcs = self._dict_functions(custom_module)
            intersecting_keys = self.funcs.keys() & custom_funcs.keys()
            if intersecting_keys:
                raise UserDefinedFunctionsError(
                    f"Unable to load user-defined functions from module {module_name}. "
                    f"The following function names are already defined by built-ins or user-defined modules: {intersecting_keys}"
                )
            self.funcs.update(custom_funcs)

    def _import_module(self, module_name):
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            raise LoadModuleError(f"Module {module_name} not found")
        except ImportError:
            raise LoadModuleError(f"Unable to import module {module_name}")
        except Exception as e:
            raise LoadModuleError(f"Error: {e}")
        else:
            return module

    def _dict_functions(self, mod):
        return {func.__name__: func for func in self._list_functions(mod)}

    def _list_functions(self, mod):
        def is_module_function(mod, func):
            return inspect.isfunction(func) and inspect.getmodule(func) == mod

        return [func for func in mod.__dict__.values() if is_module_function(mod, func)]


FUNCTIONS_MANAGER = FunctionsManager()
