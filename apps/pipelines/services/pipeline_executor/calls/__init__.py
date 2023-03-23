import logging
import re
from typing import Any

from api.exceptions import OpenAIRequestException
from api.services import OpenAICacheService
from dblogs.handlers import DatabaseLogHandler
from pipelines.builtins import (
    call_builtin_function,
    get_arg_name_by_index,
    get_arity_of_function,
)
from pipelines.models import BuiltinFunction, Prompt
from pipelines.services.exceptions import CallBuiltinFunctionError, CallPromptError

logger = logging.getLogger("db")


class CallBuiltinFunction:
    def __init__(self, builtin_fn: BuiltinFunction):
        self.builtin_fn = builtin_fn

    def __str__(self):
        return self.builtin_fn.name

    def get_arity_of_function(self):
        return get_arity_of_function(self.builtin_fn.name)

    def __call__(self, *args, **kwargs) -> Any:
        result = ""

        DatabaseLogHandler.log_fn_call_started(
            logger, self.builtin_fn.name, "builtin", kwargs
        )

        try:
            result = call_builtin_function(self.builtin_fn.name, **kwargs)
        except Exception as exc:
            error = f"An error occurred while calling the function '{self.builtin_fn.name}'. Details: {exc}"
            raise CallBuiltinFunctionError(error)
        finally:
            DatabaseLogHandler.log_fn_call_completed(logger, result)

        return result

    def get_arg_name_by_index(self, index):
        return get_arg_name_by_index(self.builtin_fn.name, index)


class CallPrompt:
    ARGS_PATTERN_RX = re.compile(r"{([a-zA-Z][a-zA-Z_0-9]*)}")
    ENDPOINT = "v1/chat/completions"
    MODEL = "gpt-3.5-turbo"

    def __init__(self, prompt_fn: Prompt):
        self.prompt_fn = prompt_fn
        self.arg_names = None

    def __str__(self):
        return self.prompt_fn.name

    def get_arity_of_function(self):
        self._prepare_arg_names()
        return len(self.arg_names)

    def get_arg_names(self):
        self._prepare_arg_names()
        return self.arg_names

    def _prepare_arg_names(self):
        if self.arg_names is None:
            self.arg_names = list(
                set(self.ARGS_PATTERN_RX.findall(self.prompt_fn.body))
            )

    def __call__(self, *args, **kwargs) -> Any:
        openaikey = kwargs.pop("openaikey")
        user = kwargs.pop("user")

        body = self.prompt_fn.body
        result = ""

        DatabaseLogHandler.log_fn_call_started(
            logger, self.prompt_fn.name, "prompt", kwargs
        )

        try:
            prompt = body.format(**kwargs)
            openai_cache_service = OpenAICacheService(
                endpoint=self.ENDPOINT,
                parameters={
                    "model": self.MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            log_instance = openai_cache_service.run(openaikey=openaikey, user=user)
            result = log_instance.response

        except (KeyError, OpenAIRequestException) as exc:
            error_msg = f"An error occurred while calling the function '{self.prompt_fn.name}'. Details: {exc}"
            raise CallPromptError(error_msg)
        finally:
            DatabaseLogHandler.log_fn_call_completed(logger, result)

        return result
