import logging.handlers
from enum import Enum

from django.utils import timezone


class DatabaseLogHandler(logging.Handler):
    class Event(Enum):
        STARTED = 1
        FN_CALL = 2
        COMPLETED = 3

    HANDLERS_MAP = {
        Event.STARTED: "event_started_handler",
        Event.FN_CALL: "fn_call_handler",
        Event.COMPLETED: "completed_handler",
    }

    def event_started_handler(self, meta_info):
        from core.models import OpenAIKey
        from dblogs.models import PipelineExecution
        from pipelines.models import PipelineSource

        kwargs = {
            "user": meta_info["user"],
            "pipeline": PipelineSource.objects.get(pk=meta_info["pipeline_id"]),
            "status": "error",
            "openai_key": OpenAIKey.objects.get(key=meta_info["openai_key"]),
            "parameters": self._preprocess_parameters(meta_info["parameters"]),
        }

        self.pipeline_execution_instance = PipelineExecution.objects.create(**kwargs)

    def fn_call_handler(self, meta_info):
        from dblogs.models import LogEntry

        LogEntry.objects.create(
            fn_name=meta_info["fn_name"],
            fn_type=meta_info["fn_type"],
            pipeline_execution_id=self.pipeline_execution_instance.pk,
            parameters=self._preprocess_parameters(meta_info["parameters"]),
        )

    def completed_handler(self, meta_info):
        self.pipeline_execution_instance.status = meta_info["status"]
        self.pipeline_execution_instance.output = (
            self._preprocess_string_value(meta_info["output"]),
        )
        self.pipeline_execution_instance.error = meta_info["error"]
        self.pipeline_execution_instance.end_date = timezone.now()
        self.pipeline_execution_instance.save()

    def __init__(self):
        super().__init__()
        self.pipeline_execution_instance = None

    def emit(self, record):
        meta_info = getattr(record, "meta_info", None)
        event = record.msg

        if not (handler := self.HANDLERS_MAP.get(event)):
            raise NotImplementedError()

        handler = getattr(self, handler)
        handler(meta_info)

    def _preprocess_parameters(self, params, max_length=250):
        return {
            key: self._preprocess_string_value(value, max_length)
            for key, value in params.items()
        }

    def _preprocess_string_value(self, param, max_length=250):
        return param[: max_length - 3] + "..." if len(param) > max_length else param
