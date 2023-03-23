from django.contrib import admin

from .models import BuiltinFunction, DAGEdge, DAGNode, PipelineSource, Prompt

admin.site.register(Prompt)
admin.site.register(DAGNode)
admin.site.register(BuiltinFunction)
admin.site.register(DAGEdge)


@admin.register(PipelineSource)
class PipelineSourceAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "body", "owner", "date_created", "date_updated"]
