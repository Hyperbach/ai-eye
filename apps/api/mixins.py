from rest_framework.exceptions import ValidationError

from .models import Log


class PrepareParametersMixin:

    ALLOWED_OPENAI_ENDPOINTS = [
        "v1/completions",
        "v1/edits",
    ]

    def prepare_parameters(self, parameters):
        endpoint = self.kwargs["endpoint"]
        if endpoint not in self.ALLOWED_OPENAI_ENDPOINTS:
            raise ValidationError("Invalid data")

        if not parameters:
            raise ValidationError("Invalid data")

        return Log.stringify_parameters(parameters)
