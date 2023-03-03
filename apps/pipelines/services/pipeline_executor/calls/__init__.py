import re
from typing import Any

from api.exceptions import OpenAIRequestException
from api.services import openai_request
from pipelines.builtins import (
    call_builtin_function,
    get_arg_name_by_index,
    get_arity_of_function,
)
from pipelines.services.exceptions import CallBuiltinFunctionError, CallPromptError


class CallBuiltinFunction:
    def __init__(self, builtin_fn):
        self.builtin_fn = builtin_fn

    def __str__(self):
        return self.builtin_fn.name

    def get_arity_of_function(self):
        return get_arity_of_function(self.builtin_fn.name)

    def __call__(self, *args, **kwargs) -> Any:
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
    ENDPOINT = "v1/completions"
    MODEL = "text-davinci-003"

    def __init__(self, prompt_fn):
        self.prompt_fn = prompt_fn

    def __str__(self):
        return self.prompt_fn.name

    def get_arity_of_function(self):
        arg_names = self.ARGS_PATTERN_RX.findall(self.prompt_fn.body)
        return len(set(arg_names))

    def __call__(self, *args, **kwargs) -> Any:
        openaikey = kwargs.pop("openaikey")
        body = self.prompt_fn.body

        try:
            prompt = body.format(**kwargs)
            return openai_request(
                openaikey=openaikey,
                endpoint=self.ENDPOINT,
                parameters={"model": self.MODEL, "prompt": prompt},
            )
        except (KeyError, OpenAIRequestException) as exc:
            raise CallPromptError(
                f"An error occurred while calling the function '{self.prompt_fn.name}'. Details: {exc}"
            )
