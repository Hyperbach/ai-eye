from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from lark import LarkError
from pipelines.models import PipelineSource
from pipelines.services.dag_builder import DAGBuilder
from pipelines.services.dag_saver import DAGSaver


class PipelineCreateForm(forms.ModelForm):
    class Meta:
        model = PipelineSource
        fields = ("body",)

    def clean(self):
        cleaned_data = super().clean()
        body = cleaned_data.get("body")
        if not body:
            raise ValidationError("Invalid body provided.")

        dag_builder = DAGBuilder()

        try:
            self.cleaned_data["root"] = dag_builder.build(body)
        except LarkError as exc:
            raise ValidationError(f"Unable to parse specified body. Details: {exc}")

        return cleaned_data

    def save(self, commit=True):
        update = self.instance.id is not None

        pipeline = super().save(commit=False)
        if commit:
            dag_saver = DAGSaver(self.cleaned_data["root"])
            with transaction.atomic():
                pipeline.save()
                dag_saver.save(pipeline=pipeline, update=update)

        return pipeline
