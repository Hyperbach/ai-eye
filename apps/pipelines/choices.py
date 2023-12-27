from typing import Tuple

from django.db import models
from django.utils.translation import gettext_lazy as _


class TypesOfDAGNodes(models.IntegerChoices):
    PROMPT = 0, "Prompt"
    BUILTIN_FUNCTION = 1, "Builtin Function"
    PLACEHOLDER = 2, "Placeholder"


class AIServices(models.TextChoices):
    OPENAI = "openai", _("OpenAI")
    TOGETHERAI = "togetherai", _("TogetherAI")

    @staticmethod
    def get_base_url(service):
        urls = {
            AIServices.OPENAI: "https://api.openai.com",
            AIServices.TOGETHERAI: "https://api.together.xyz"
        }
        return urls.get(service, None)


class TypesOfModels(models.TextChoices):
    # OpenAI Models
    GPT_4_TURBO_1106 = "gpt-4-1106-preview", _("GPT-4 Turbo 1106")
    GPT_4_1106_VISION_PREVIEW = "gpt-4-1106-vision-preview", _("GPT-4 1106 Vision Preview")
    GPT_4 = "gpt-4", _("GPT-4")
    GPT_4_32K = "gpt-4-32k", _("GPT-4 32K")
    GPT_35_TURBO_1106 = "gpt-3.5-turbo-1106", _("GPT-3.5 Turbo 1106")
    GPT_35_TURBO_INSTRUCT = "gpt-3.5-turbo-instruct", _("GPT-3.5 Turbo Instruct")

    # Together.ai / MistralAI Models
    MISTRAL_7B_INSTRUCT_V02 = "mistralai/Mistral-7B-Instruct-v0.2", _("Mistral (7B) Instruct v0.2	")
    MIXTRAL_8X7B_INSTRUCT = "mistralai/Mixtral-8x7B-Instruct-v0.1", _("Mixtral 8x7B Instruct")
    MIXTRAL_8X7B = "mistralai/Mixtral-8x7B-v0.1", _("Mixtral MoE 8x7B	")

    def get_service_for_model(self):
        return MODEL_TO_SERVICE_MAPPING.get(self, None)

    def get_pricing_details(self) -> Tuple[float, float]:
        pricing: dict[str, Tuple[float, float]] = {
            "gpt-4-1106-preview": (0.01, 0.03),
            "gpt-4-1106-vision-preview": (0.01, 0.03),
            "gpt-4": (0.03, 0.06),
            "gpt-4-32k": (0.06, 0.12),
            "gpt-3.5-turbo-1106": (0.0010, 0.0020),
            "gpt-3.5-turbo-instruct": (0.0015, 0.0020),
            "mistralai/Mistral-7B-Instruct-v0.2": (0.0002, 0.0002),
            "mistralai/Mixtral-8x7B-Instruct-v0.1": (0.0006, 0.0006),
            "mistralai/Mixtral-8x7B-v0.1": (0.0006, 0.0006),
        }
        return pricing.get(str(self.value), (0.0, 0.0))

    def get_model_name(self):
        return self.value

    def get_base_url(self):
        service_instance = self.get_service_for_model()
        return service_instance.get_base_url(service_instance)

    def display_name(self):
        return _(self.label)


MODEL_TO_SERVICE_MAPPING = {
    TypesOfModels.GPT_4_TURBO_1106: AIServices.OPENAI,
    TypesOfModels.GPT_4_1106_VISION_PREVIEW: AIServices.OPENAI,
    TypesOfModels.GPT_4: AIServices.OPENAI,
    TypesOfModels.GPT_4_32K: AIServices.OPENAI,
    TypesOfModels.GPT_35_TURBO_1106: AIServices.OPENAI,
    TypesOfModels.GPT_35_TURBO_INSTRUCT: AIServices.OPENAI,
    TypesOfModels.MISTRAL_7B_INSTRUCT_V02: AIServices.TOGETHERAI,
    TypesOfModels.MIXTRAL_8X7B_INSTRUCT: AIServices.TOGETHERAI,
    TypesOfModels.MIXTRAL_8X7B: AIServices.TOGETHERAI,
}
