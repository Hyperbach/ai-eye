from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.models import TimestampMixin
from pipelines.choices import TypesOfDAGNodes, TypesOfGPTModels
from pipelines.services.functions_manager import FUNCTIONS_MANAGER
from pipelines.validators import FunctionNameValidator

User = get_user_model()


class Prompt(TimestampMixin):
    """
    A user's defined prompt function
    """

    name: models.CharField = models.CharField(
        max_length=100, unique=True, validators=[FunctionNameValidator()]
    )
    description: models.TextField = models.TextField(blank=True)
    body: models.TextField = models.TextField()
    owner: models.ForeignKey = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name=_("author of the prompt")
    )
    type = models.IntegerField(
        default=TypesOfGPTModels.GPT_35_TURBO_1106, choices=TypesOfGPTModels.choices
    )

    class Meta:
        verbose_name = _("Prompt")
        verbose_name_plural = _("Prompts")

    def __str__(self):
        return self.name

    def clean(self):
        name = self.name
        if BuiltinFunction.objects.filter(name=name).exists():
            raise ValidationError("BuiltinFunction with this name already exists.")


class BuiltinFunction(TimestampMixin):
    """
    Pre-defined function residing on an FS
    """

    name: models.CharField = models.CharField(
        max_length=100,
        unique=True,
        validators=[FunctionNameValidator()],
    )
    description: models.TextField = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Builtin Function")
        verbose_name_plural = _("Builtin Functions")

    def __str__(self):
        return self.name

    def clean(self):
        name = self.name
        if Prompt.objects.filter(name=name).exists():
            raise ValidationError("Prompt with this name already exists.")

    def get_fn_type(self):
        is_builtin_fn = FUNCTIONS_MANAGER.is_builtin_function(self.name)
        return "Built-in" if is_builtin_fn else "User-defined"


class PipelineSource(TimestampMixin):
    """
    Represents a source of DAG nodes and edges
    """

    body: models.TextField = models.TextField()
    owner: models.ForeignKey = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name=_("Author of the Pipeline")
    )
    name: models.CharField = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = _("PipelineSource")
        verbose_name_plural = _("PipelineSources")

    def __str__(self):
        return self.body

    def delete_dependents(self):
        with transaction.atomic():
            DAGEdge.objects.filter(
                Q(from_node__pipeline_source=self) | Q(to_node__pipeline_source=self)
            ).delete()

            DAGNode.objects.filter(pipeline_source=self).delete()

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            self.delete_dependents()
            super().delete(*args, **kwargs)


class DAGNode(models.Model):
    """
    Represents a node in a DAG
    """

    type = models.IntegerField(
        default=TypesOfDAGNodes.PROMPT, choices=TypesOfDAGNodes.choices
    )

    identifier = models.PositiveIntegerField()
    name = models.CharField(max_length=150)
    pipeline_source = models.ForeignKey(
        PipelineSource, on_delete=models.CASCADE, related_name="nodes"
    )

    class Meta:
        verbose_name = _("DAGNode")
        verbose_name_plural = _("DAGNodes")
        constraints = [
            models.UniqueConstraint(
                fields=["type", "name", "identifier", "pipeline_source"],
                name="unique_dagnodes",
            )
        ]

    def __str__(self):
        return f"{self.name} {self.identifier}"


class DAGEdge(models.Model):
    """
    Represents an edge in a DAG
    """

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
