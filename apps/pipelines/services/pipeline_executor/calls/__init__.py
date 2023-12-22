import json
import logging
import re
from typing import Any

from api.exceptions import OpenAIRequestException
from api.services import AICacheService
from dblogs.handlers import DatabaseLogHandler
from pipelines.choices import TypesOfModels
from pipelines.models import BuiltinFunction, Prompt
from pipelines.services.exceptions import CallBuiltinFunctionError, CallPromptError
from pipelines.services.functions_manager import FUNCTIONS_MANAGER

logger = logging.getLogger("db")


class CallBuiltinFunction:
    def __init__(self, builtin_fn: BuiltinFunction):
        self.builtin_fn = builtin_fn

    def __str__(self):
        return self.builtin_fn.name

    def get_arity_of_function(self):
        try:
            return FUNCTIONS_MANAGER.get_arity_of_function(self.builtin_fn.name)
        except Exception as exc:
            error = f"An error occurred while calling the function '{self.builtin_fn.name}'. Details: {exc}"
            raise CallBuiltinFunctionError(error)

    def __call__(self, *args, **kwargs) -> Any:
        result = ""

        openaikey = kwargs.pop("openaikey", None)
        prompts = kwargs.pop("prompts", None)

        DatabaseLogHandler.log_fn_call_started(
            logger, self.builtin_fn.name, "builtin", kwargs
        )

        target_function = FUNCTIONS_MANAGER.get_function(self.builtin_fn.name)
        if hasattr(target_function, "needs_context") and target_function.needs_context:
            context = {
                "openaikey": openaikey,
                "prompts": prompts,
                "functions": FUNCTIONS_MANAGER.funcs,  # Add all available functions to the context
            }
            setattr(target_function, "context", context)

        try:
            result = FUNCTIONS_MANAGER.call_builtin_function(
                name=self.builtin_fn.name, **kwargs
            )
        except Exception as exc:
            error = f"An error occurred while calling the function '{self.builtin_fn.name}'. Details: {exc}"
            raise CallBuiltinFunctionError(error)
        finally:
            DatabaseLogHandler.log_fn_call_completed(logger, result)

        return result

    def get_arg_name_by_index(self, index):
        return FUNCTIONS_MANAGER.get_arg_name_by_index(self.builtin_fn.name, index)


class CallPrompt:
    ARGS_PATTERN_RX = re.compile(r"{([a-zA-Z][a-zA-Z_0-9]*)}")
    ENDPOINT = "v1/chat/completions"

    def __init__(self, prompt_fn: Prompt):
        self.prompt_fn = prompt_fn
        self.arg_names = None

        model_choice = TypesOfModels(prompt_fn.type)
        self.model_name = model_choice.get_model_name()
        self.base_url = model_choice.get_base_url()

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

        DatabaseLogHandler.log_fn_call_started(
            logger, self.prompt_fn.name, "prompt", kwargs
        )

        prompt_tokens = 0
        completion_tokens = 0
        full_response = ""
        text_response = ""

        try:
            prompt = body.format(**kwargs)

            openai_cache_service = AICacheService(
                base_url=self.base_url,
                endpoint=self.ENDPOINT,
                parameters={"model": self.model_name, "messages": [{"role": "user", "content": prompt}]},
                model=self.model_name,
            )
            log_instance = openai_cache_service.run(apikey=openaikey, user=user)

            response = json.loads(log_instance.response)

            text_response = response

            # Check if response is a dictionary (to handle cases where response might be a string)
            if isinstance(response, dict):
                # Extract text response from 'choices'
                text_response = None
                if 'choices' in response and response['choices']:
                    text_contents = [choice['message']['content'] for choice in response['choices'] if
                                     'content' in choice['message']]
                    text_response = ' '.join(text_contents)

                # Safely extract prompt_tokens and completion_tokens
                usage_data = response.get('usage', {})
                prompt_tokens = usage_data.get('prompt_tokens', 0)
                completion_tokens = usage_data.get('completion_tokens', 0)
                full_response = response  # Store the full response

        except (KeyError, OpenAIRequestException) as exc:
            error_msg = f"An error occurred while calling the function '{self.prompt_fn.name}'. Details: {exc}"
            raise CallPromptError(error_msg)
        finally:
            DatabaseLogHandler.log_fn_call_completed(logger, {"text_response": text_response,
                                                              "prompt_tokens": prompt_tokens,
                                                              "completion_tokens": completion_tokens,
                                                              "full_response": full_response})

        return text_response
