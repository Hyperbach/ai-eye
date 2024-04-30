import json
import logging
import re
from typing import Any

from api.exceptions import ApiRequestException
from api.services import AICacheService
from dblogs.handlers import DatabaseLogHandler
from pipelines.choices import TypesOfModels
from pipelines.models import BuiltinFunction, Prompt
from pipelines.services.exceptions import CallBuiltinFunctionError, CallPromptError
from pipelines.services.functions_manager import FUNCTIONS_MANAGER
from pipelines.utils import strip_json_response

logger = logging.getLogger("db")
console_logger = logging.getLogger("console")


class CallBuiltinFunction:
    def __init__(self, builtin_fn: BuiltinFunction):
        self.builtin_fn = builtin_fn

    def __str__(self):
        return self.builtin_fn.name

    def get_arity_of_function(self):
        try:
            return FUNCTIONS_MANAGER.get_arity_of_function(self.builtin_fn.name)
        except Exception as exc:
            error = f"An error occurred while getting arity of the function '{self.builtin_fn.name}'. Details: {exc}"
            raise CallBuiltinFunctionError(error)

    def __call__(self, *args, **kwargs) -> Any:
        result = ""

        DatabaseLogHandler.log_fn_call_started(
            logger, self.builtin_fn.name, "builtin", None, kwargs
        )

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

    @staticmethod
    def get_api_key_for_prompt(public_token, prompt):
        # Create an instance of TypesOfModels using the prompt type
        model_type = TypesOfModels(prompt.type)

        # Get the service for this model type
        service_type = model_type.get_service_for_model()

        # Construct the attribute name dynamically based on the service type
        api_key_field = f"{service_type}key"

        # Retrieve the corresponding API key from the PublicToken object
        api_key = getattr(public_token, api_key_field, None)

        return api_key.key

    def __call__(self, *args, **kwargs) -> Any:
        publictoken_str = kwargs.pop("apikey")
        apikey = CallPrompt.get_api_key_for_prompt(publictoken_str, self.prompt_fn)

        user = kwargs.pop("user")

        body = self.prompt_fn.body

        DatabaseLogHandler.log_fn_call_started(
            logger, self.prompt_fn.name, "prompt", self.model_name, kwargs
        )

        prompt_tokens = 0
        completion_tokens = 0
        prompt_cost = 0
        completion_cost = 0
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
            log_instance = openai_cache_service.run(apikey=apikey, user=user)

            response = json.loads(log_instance.response)

            text_response = response

            # Check if response is a dictionary (to handle cases where response might be a string)
            if isinstance(response, dict):
                # Extract text response from 'choices'
                text_response = None
                if 'choices' in response and response['choices']:
                    text_contents = [choice['message']['content'] for choice in response['choices'] if
                                     'content' in choice['message']]
                    text_response = ''.join(text_contents)
                    # use strict=True only when json=True (not implemented yet)
                    text_response = strip_json_response(text_response, strict=False)

                # Safely extract prompt_tokens and completion_tokens
                usage_data = response.get('usage', {})
                prompt_tokens = usage_data.get('prompt_tokens', 0)
                completion_tokens = usage_data.get('completion_tokens', 0)

                model_type = TypesOfModels(self.prompt_fn.type)
                cost = model_type.get_pricing_details()
                console_logger.info(f"Cost: {cost}")
                prompt_cost = prompt_tokens * cost[0] / 1000
                completion_cost = completion_tokens * cost[1] / 1000

                console_logger.info(f"Prompt cost calculation: {prompt_tokens} * {cost[0]} / 1000 = {prompt_cost}")
                console_logger.info(
                    f"Completion cost calculation: {completion_tokens} * {cost[1]} / 1000 = {completion_cost}")

                full_response = response  # Store the full response

        except (KeyError, ApiRequestException) as exc:
            error_msg = f"An error occurred while calling the function '{self.prompt_fn.name}'. Details: {exc}"
            raise CallPromptError(error_msg)
        finally:
            DatabaseLogHandler.log_fn_call_completed(logger, {"text_response": text_response,
                                                              "prompt_tokens": prompt_tokens,
                                                              "completion_tokens": completion_tokens,
                                                              "prompt_cost": prompt_cost,
                                                              "completion_cost": completion_cost,
                                                              "full_response": full_response})

        return text_response
