from django.db import models


class TypesOfDAGNodes(models.IntegerChoices):
    PROMPT = 0, "Prompt"
    BUILTIN_FUNCTION = 1, "Builtin Function"
    PLACEHOLDER = 2, "Placeholder"


# these string values should be valid GPT models names
class TypesOfGPTModels(models.IntegerChoices):
    GPT_35_TURBO_1106 = 0, "gpt-3.5-turbo-1106"
    GPT_4 = 1, "gpt-4"
