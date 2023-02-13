from rest_framework.exceptions import ValidationError

from .models import Log


class PrepareParametersMixin:

    ALLOWED_OPENAI_ENDPOINTS = [
        "v1/completions",
        "v1/edits",
    ]

    def prepare_parameters(self):
        endpoint = self.kwargs["endpoint"]
        if endpoint not in self.ALLOWED_OPENAI_ENDPOINTS:
            raise ValidationError("Invalid data")

        if not self.request.data:
            raise ValidationError("Invalid data")
        if (
            "api_type" not in self.request.data
            or type(self.request.data["api_type"]) is not str
        ):
            raise ValidationError("Invalid data")

        parameters = {k: v for k, v in self.request.data.items() if k != "api_type"}
        parameters_stringified = Log.stringify_parameters(parameters)

        return parameters, parameters_stringified
