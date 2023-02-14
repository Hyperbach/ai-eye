from rest_framework.exceptions import ValidationError

from .models import Log


class PrepareParametersMixin:

    ALLOWED_OPENAI_ENDPOINTS = [
        "v1/completions",
        "v1/edits",
    ]

    def prepare_parameters(self, data):
        endpoint = self.kwargs["endpoint"]
        if endpoint not in self.ALLOWED_OPENAI_ENDPOINTS:
            raise ValidationError("Invalid data")

        if not data:
            raise ValidationError("Invalid data")

        parameters = data
        parameters_stringified = Log.stringify_parameters(parameters)

        return parameters, parameters_stringified
