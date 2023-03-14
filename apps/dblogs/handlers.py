import logging.handlers


class DatabaseLogHandler(logging.Handler):
    model_name = None

    def __init__(self, model=""):
        super().__init__()
        self.model_name = model

    def emit(self, record):
        if self.model_name:
            try:
                model = self.get_model(self.model_name)
            except Exception:
                from .models import LogMessage as model
        else:
            from .models import LogMessage as model

        levelname = record.levelname.lower()
        message = self.format(record)
        meta_info = getattr(record, "meta_info", None)

        log_entry = model(level=levelname, message=message, meta_info=meta_info)
        log_entry.save()

    @staticmethod
    def get_model(name):
        names = name.split(".")
        mod = __import__(".".join(names[:-1]), fromlist=names[-1:])
        return getattr(mod, names[-1])
