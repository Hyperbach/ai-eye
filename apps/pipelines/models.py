from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import IsActiveMixin, TimestampMixin
from pipelines.builtins import get_builtin_function_names

User = get_user_model()


class Prompt(TimestampMixin, IsActiveMixin):
    """
    A user's defined prompt function
    """

    name: models.CharField = models.CharField(max_length=100, unique=True)
    description: models.TextField = models.TextField(blank=True)
    body: models.TextField = models.TextField()
    # an author of a prompt
    owner: models.ForeignKey = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Prompt")
        verbose_name_plural = _("Prompts")

    def __str__(self):
        return self.name

    def clean(self):
        name = self.name
        if BuiltinFunction.objects.filter(name=name).exists():
            raise ValidationError("BuiltinFunction with this name already exists.")


class BuiltinFunction(TimestampMixin, IsActiveMixin):
    name: models.CharField = models.CharField(
        max_length=100, choices=get_builtin_function_names(), unique=True
    )
    description: models.TextField = models.TextField(blank=True)

    """
    Pre-defined function residing on an FS
    """

    class Meta:
        verbose_name = _("Builtin Function")
        verbose_name_plural = _("Builtin Functions")

    def __str__(self):
        return self.name

    def clean(self):
        name = self.name
        if Prompt.objects.filter(name=name).exists():
            raise ValidationError("Prompt with this name already exists.")


class PipelineSource(TimestampMixin):
    body: models.TextField = models.TextField()

    class Meta:
        verbose_name = _("PipelineSource")
        verbose_name_plural = _("PipelineSources")

    def __str__(self):
        return f"{self.body[:5]}..."


class TypesOfDAGNodes(models.IntegerChoices):
    PROMPT = 0, "Prompt"
    BUILTIN_FUNCTION = 1, "Builtin Function"


class DAGNode(models.Model):

    type = models.IntegerField(
        default=TypesOfDAGNodes.PROMPT, choices=TypesOfDAGNodes.choices
    )

    full_name = models.CharField(max_length=50)
    name = models.CharField(max_length=150)
    pipeline_source = models.ForeignKey(
        PipelineSource, on_delete=models.CASCADE, related_name="nodes"
    )

    class Meta:
        verbose_name = _("DAGNode")
        verbose_name_plural = _("DAGNodes")
        constraints = [
            models.UniqueConstraint(
                fields=["type", "full_name", "pipeline_source"], name="unique_dagnodes"
            )
        ]

    def __str__(self):
        return self.name


class DAGEdge(models.Model):
    from_node = models.ForeignKey(
        DAGNode, related_name="from_edges", on_delete=models.CASCADE
    )
    to_node = models.ForeignKey(
        DAGNode, related_name="to_edges", on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("DAGEdge")
        verbose_name_plural = _("DAGEdges")

    def __str__(self):
        return f"{self.from_node} -> {self.to_node}"
