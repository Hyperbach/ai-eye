import logging

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from lark import LarkError

from pipelines.models import PipelineSource, Document, Assistant, Tag
from pipelines.services.dag_builder import DAGBuilder
from pipelines.services.dag_saver import DAGSaver

console_logger = logging.getLogger("console")


class PipelineCreateForm(forms.ModelForm):
    tags = forms.CharField(help_text="Enter tags separated by commas", required=False)

    class Meta:
        model = PipelineSource
        fields = ("name", "body")

    def __init__(self, *args, **kwargs):
        super(PipelineCreateForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['tags'].initial = ', '.join([tag.name for tag in self.instance.tags.all()])

    def clean(self):
        cleaned_data = super().clean()
        body = cleaned_data.get("body")
        if not body:
            raise ValidationError("Invalid body provided.")

        dag_builder = DAGBuilder()
        try:
            self.cleaned_data["root"] = dag_builder.build(body)
        except LarkError as exc:
            raise ValidationError("Failed to parse expression: " + str(exc))

        return cleaned_data

    def save(self, commit=True):
        console_logger.info("Saving PipelineSource...")
        pipeline = super().save(commit=False)

        if commit:
            with transaction.atomic():
                console_logger.info(f"Saving pipeline instance: {pipeline}")
                pipeline.save()

                dag_saver = DAGSaver(self.cleaned_data["root"])
                dag_saver.save(pipeline=pipeline, update=self.instance.id is not None)

                self._save_tags(pipeline)
                self.save_m2m()

        return pipeline

    def _save_tags(self, pipeline):
        tag_names = [name.strip() for name in self.cleaned_data.get('tags', '').split(',')]

        for tag_name in tag_names:
            if tag_name:
                tag, created = Tag.objects.get_or_create(name=tag_name)
                pipeline.tags.add(tag)


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['description']

    file = forms.FileField()


class AssistantForm(forms.ModelForm):
    class Meta:
        model = Assistant
        fields = ['name', 'description', 'model', 'instructions', 'files', 'metadata']
