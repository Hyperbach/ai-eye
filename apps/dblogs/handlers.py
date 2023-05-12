import logging.handlers
from enum import Enum

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
        from core.models import OpenAIKey
        from dblogs.models import PipelineExecutionLog
        from pipelines.models import PipelineSource

        kwargs = {
            "user": metainfo["user"],
            "pipeline": PipelineSource.objects.get(pk=metainfo["pipeline_id"]),
            "status": "error",
            "openai_key": OpenAIKey.objects.get(key=metainfo["openai_key"]),
            "parameters": self._prepare_parameters(metainfo["parameters"]),
        }

        self.pipeline_execution_log_instance = PipelineExecutionLog.objects.create(
            **kwargs
        )

    def fn_call_started_handler(self, metainfo):
        from dblogs.models import CallEntryLog

        self.call_entry_log_instance = CallEntryLog.objects.create(
            fn_name=metainfo["fn_name"],
            fn_type=metainfo["fn_type"],
            pipeline_execution_id=self.pipeline_execution_log_instance.pk,
            parameters=self._prepare_parameters(metainfo["parameters"]),
        )

    def fn_call_completed_handler(self, metainfo):
        self.call_entry_log_instance.output = metainfo["output"]
        self.call_entry_log_instance.end_date = timezone.now()
        self.call_entry_log_instance.save(update_fields=["output", "end_date"])
        self.call_entry_log_instance = None

    def completed_handler(self, metainfo):
        self.pipeline_execution_log_instance.status = metainfo["status"]
        self.pipeline_execution_log_instance.output = self._prepare_value(
            metainfo["output"]
        )
        self.pipeline_execution_log_instance.error = metainfo["error"]
        self.pipeline_execution_log_instance.end_date = timezone.now()
        self.pipeline_execution_log_instance.save(
            update_fields=["status", "output", "error", "end_date"]
        )
        self.pipeline_execution_log_instance = None

    def __init__(self):
        super().__init__()
        self.pipeline_execution_log_instance = None
        self.call_entry_log_instance = None

    def emit(self, record):
        metainfo = getattr(record, "metainfo", None)
        event = record.msg

        if not (handler := self.HANDLERS_MAP.get(event)):
            raise NotImplementedError("Unsupported event type.")

        handler = getattr(self, handler)
        handler(metainfo)

    def _prepare_parameters(self, params, max_length=250):
        return {
            key: self._prepare_value(value, max_length) for key, value in params.items()
        }

    def _prepare_value(self, param, max_length=250):
        return param[: max_length - 3] + "..." if len(param) > max_length else param

    @staticmethod
    def log_event_started(logger, user, pipeline_id, openaikey, parameters):
        logger.info(
            msg=DatabaseLogHandler.Event.STARTED,
            extra={
                "metainfo": {
                    "user": user,
                    "pipeline_id": pipeline_id,
                    "openai_key": openaikey,
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
    def log_fn_call_started(logger, fn_name, fn_type, parameters):
        logger.info(
            msg=DatabaseLogHandler.Event.FN_CALL_STARTED,
            extra={
                "metainfo": {
                    "fn_name": fn_name,
                    "fn_type": fn_type,
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
