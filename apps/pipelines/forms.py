from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from lark import LarkError
from pipelines.models import (
    BuiltinFunction,
    DAGEdge,
    DAGNode,
    PipelineSource,
    Prompt,
    TypesOfDAGNodes,
)
from pipelines.services.dag_builder import DAGBuilder, traverse_root


class PipelineCreateForm(forms.ModelForm):
    class Meta:
        model = PipelineSource
        fields = ("body",)

    def clean(self):
        cleaned_data = super().clean()
        body = cleaned_data.get("body")
        if not body:
            raise ValidationError("Invalid body provided.")

        nodes, edges, prompts, builtins = self.parse_dag(body)

        self.cleaned_data["nodes"] = nodes
        self.cleaned_data["edges"] = edges
        self.cleaned_data["prompts"] = prompts
        self.cleaned_data["builtins"] = builtins

        return cleaned_data

    def save(self, commit=True):
        pipeline = super().save(commit=False)
        if commit:
            with transaction.atomic():
                pipeline.save()
                dag_nodes = self.create_dag_nodes(pipeline)
                self.create_dag_edges(dag_nodes)

        return pipeline

    def parse_dag(self, body):
        builder = DAGBuilder()

        try:
            root = builder.build(body)
            nodes, edges = traverse_root(root)

            # designate either builtins or prompts or placeholders
            node_names = [node.name for node in nodes]

            prompts = Prompt.objects.filter(name__in=node_names).all()
            builtins = BuiltinFunction.objects.filter(name__in=node_names).all()
        except LarkError as exc:
            raise ValidationError(f"Unable to parse specified body. Details: {exc}")
        except Exception as exc:
            raise ValidationError(
                f"Unable to parse specified body. Unknown error. Details: {exc}"
            )

        return nodes, edges, prompts, builtins

    def get_dag_node_type(self, node_name):
        def find_first(search_node_name, src_coll):
            return next(filter(lambda p: p.name == search_node_name, src_coll), None)

        prompt = find_first(node_name, self.cleaned_data["prompts"])
        builtin = find_first(node_name, self.cleaned_data["builtins"])

        if prompt is not None:
            dag_node_type = TypesOfDAGNodes.PROMPT
        elif builtin is not None:
            dag_node_type = TypesOfDAGNodes.BUILTIN_FUNCTION
        else:
            dag_node_type = TypesOfDAGNodes.PLACEHOLDER

        return dag_node_type

    def create_dag_nodes(self, pipeline):
        dag_nodes = []

        for node in self.cleaned_data["nodes"]:
            node_name = node.name
            node_full_name = node.full_name

            dag_node_type = self.get_dag_node_type(node_name)
            dagnode = DAGNode(
                full_name=node_full_name,
                name=node_name,
                type=dag_node_type,
                pipeline_source=pipeline,
            )
            dag_nodes.append(dagnode)

        if dag_nodes:
            DAGNode.objects.bulk_create(dag_nodes)
        return dag_nodes

    def create_dag_edges(self, dag_nodes):
        edges = []

        for edge in self.cleaned_data["edges"]:
            src = edge.source
            target = edge.target
            from_node = next(
                (n for n in dag_nodes if n.full_name == src.full_name), None
            )
            to_node = next(
                (n for n in dag_nodes if n.full_name == target.full_name), None
            )
            edge = DAGEdge(from_node=from_node, to_node=to_node)
            edges.append(edge)

        if edges:
            DAGEdge.objects.bulk_create(edges)
