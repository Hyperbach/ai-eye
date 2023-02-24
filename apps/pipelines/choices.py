from django.db import models


class TypesOfDAGNodes(models.IntegerChoices):
    PROMPT = 0, "Prompt"
    BUILTIN_FUNCTION = 1, "Builtin Function"
    PLACEHOLDER = 2, "Placeholder"
