import logging.handlers
import threading
from enum import Enum

from django.db.models import Sum
from django.utils import timezone


class DatabaseLogHandler(logging.Handler):
    class Event(Enum):
        STARTED = 1
        FN_CALL_STARTED = 2
        FN_CALL_COMPLETED = 3
        COMPLETED = 4

    HANDLERS_MAP = {
        Event.STARTED: "event_started_handler",
        Event.FN_CALL_STARTED: "fn_call_started_handler",
        Event.FN_CALL_COMPLETED: "fn_call_completed_handler",
        Event.COMPLETED: "completed_handler",
    }

    def event_started_handler(self, metainfo):
        from core.models import PublicToken
        from dblogs.models import PipelineExecutionLog
        from pipelines.models import PipelineSource

        apikey_str = metainfo["apikey"]
        apikey = PublicToken.objects.get(key=apikey_str)

        kwargs = {
            "user": metainfo["user"],
            "pipeline": PipelineSource.objects.get(pk=metainfo["pipeline_id"]),
            "status": "error",
            "apikey": apikey,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_prompt_cost": 0,
            "total_completion_cost": 0,
            "total_cost": 0,
            "total_tokens": 0,
            "parameters": self._prepare_parameters(metainfo["parameters"]),
        }

        self.local.pipeline_execution_log_instance = PipelineExecutionLog.objects.create(
            **kwargs
        )

    def fn_call_started_handler(self, metainfo):
        from dblogs.models import CallEntryLog

        self.local.call_entry_log_instance = CallEntryLog.objects.create(
            fn_name=metainfo["fn_name"],
            fn_type=metainfo["fn_type"],
            prompt_tokens=0,
            completion_tokens=0,
            prompt_cost=0,
            completion_cost=0,
            model=metainfo["model"],
            pipeline_execution_id=self.local.pipeline_execution_log_instance.pk,
            parameters=self._prepare_parameters(metainfo["parameters"]),
        )

    def fn_call_completed_handler(self, metainfo):
        output = metainfo["output"]

        # Initialize default values
        text_response = None
        prompt_tokens = 0
        completion_tokens = 0
        prompt_cost = 0
        completion_cost = 0
        model = None
        full_response = output  # Default to the output itself

        # Check if output is a dictionary
        if isinstance(output, dict):
            text_response = output.get("text_response", "")
            prompt_tokens = output.get("prompt_tokens", 0)
            completion_tokens = output.get("completion_tokens", 0)
            prompt_cost = output.get("prompt_cost", 0)
            completion_cost = output.get("completion_cost", 0)
            model = output.get("model", None)
            full_response = output.get("full_response", output)

        # In case output is a string, use it as the text response
        elif isinstance(output, str):
            text_response = output

        # Update the call_entry_log_instance
        self.local.call_entry_log_instance.output = text_response
        self.local.call_entry_log_instance.prompt_tokens = prompt_tokens
        self.local.call_entry_log_instance.completion_tokens = completion_tokens
        self.local.call_entry_log_instance.prompt_cost = prompt_cost
        self.local.call_entry_log_instance.completion_cost = completion_cost
        self.local.call_entry_log_instance.model = model
        self.local.call_entry_log_instance.full_response = full_response

        self.local.call_entry_log_instance.end_date = timezone.now()
        self.local.call_entry_log_instance.save(
            update_fields=["output", "end_date",
                           "prompt_tokens", "completion_tokens",
                           "prompt_cost", "completion_cost",
                           "full_response"])

    def completed_handler(self, metainfo):
        from dblogs.models import CallEntryLog

        # Sum up the token usage from all function calls related to this pipeline execution
        total_prompt_tokens = CallEntryLog.objects.filter(
            pipeline_execution_id=self.local.pipeline_execution_log_instance.pk
        ).aggregate(sum_prompt_tokens=Sum('prompt_tokens'))['sum_prompt_tokens'] or 0

        total_completion_tokens = CallEntryLog.objects.filter(
            pipeline_execution_id=self.local.pipeline_execution_log_instance.pk
        ).aggregate(sum_completion_tokens=Sum('completion_tokens'))['sum_completion_tokens'] or 0

        total_prompt_cost = CallEntryLog.objects.filter(
            pipeline_execution_id=self.local.pipeline_execution_log_instance.pk
        ).aggregate(sum_prompt_cost=Sum('prompt_cost'))['sum_prompt_cost'] or 0

        total_completion_cost = CallEntryLog.objects.filter(
            pipeline_execution_id=self.local.pipeline_execution_log_instance.pk
        ).aggregate(sum_completion_cost=Sum('completion_cost'))['sum_completion_cost'] or 0

        # Update the pipeline_execution_log_instance with the total tokens used
        self.local.pipeline_execution_log_instance.total_prompt_tokens = total_prompt_tokens
        self.local.pipeline_execution_log_instance.total_completion_tokens = total_completion_tokens
        self.local.pipeline_execution_log_instance.total_tokens = total_prompt_tokens + total_completion_tokens

        self.local.pipeline_execution_log_instance.total_prompt_cost = total_prompt_cost
        self.local.pipeline_execution_log_instance.total_completion_cost = total_completion_cost
        self.local.pipeline_execution_log_instance.total_cost = total_prompt_cost + total_completion_cost

        # Update the status, output, error, and end_date for the pipeline_execution_log_instance
        self.local.pipeline_execution_log_instance.status = metainfo["status"]
        self.local.pipeline_execution_log_instance.output = metainfo["output"]
        self.local.pipeline_execution_log_instance.error = metainfo["error"]
        self.local.pipeline_execution_log_instance.end_date = timezone.now()

        # Save the updated fields
        self.local.pipeline_execution_log_instance.save(
            update_fields=["status", "output", "error", "end_date",
                           "total_prompt_tokens", "total_completion_tokens", "total_tokens",
                           "total_prompt_cost", "total_completion_cost", "total_cost"]
        )

    def __init__(self):
        super().__init__()
        self.local = threading.local()

    def emit(self, record):
        metainfo = getattr(record, "metainfo", None)
        event = record.msg

        if not (handler := self.HANDLERS_MAP.get(event)):
            raise NotImplementedError(f"Unsupported event type: {event}")

        handler = getattr(self, handler)
        handler(metainfo)

    def _prepare_parameters(self, params):
        return {
            key: value for key, value in params.items()
        }

    @staticmethod
    def log_event_started(logger, user, pipeline_id, apikey, parameters):
        logger.info(
            msg=DatabaseLogHandler.Event.STARTED,
            extra={
                "metainfo": {
                    "user": user,
                    "pipeline_id": pipeline_id,
                    "apikey": apikey,
                    "parameters": parameters,
                }
            },
        )

    @staticmethod
    def log_event_completed(logger, output, error):
        logger.info(
            msg=DatabaseLogHandler.Event.COMPLETED,
            extra={
                "metainfo": {
                    "output": output,
                    "error": error,
                    "status": "success" if not error else "error",
                }
            },
        )

    @staticmethod
    def log_fn_call_started(logger, fn_name, fn_type, model, parameters):
        logger.info(
            msg=DatabaseLogHandler.Event.FN_CALL_STARTED,
            extra={
                "metainfo": {
                    "fn_name": fn_name,
                    "fn_type": fn_type,
                    "model": model,
                    "parameters": parameters,
                }
            },
        )

    @staticmethod
    def log_fn_call_completed(logger, output):
        logger.info(
            msg=DatabaseLogHandler.Event.FN_CALL_COMPLETED,
            extra={
                "metainfo": {
                    "output": output,
                }
            },
        )
