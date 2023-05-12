import re

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class FunctionNameValidator:
    NAME_PATTERN_RX = re.compile(r"[a-zA-Z][a-zA-Z_0-9]*")

    def __call__(self, value):
        if not self.NAME_PATTERN_RX.match(value):
            raise ValidationError(
                _(
                    "The name must start with a letter and contain only letters, digits, or underscores."
                )
            )
