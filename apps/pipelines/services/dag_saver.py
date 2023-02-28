from pipelines.choices import TypesOfDAGNodes
from pipelines.models import BuiltinFunction, DAGEdge, DAGNode, PipelineSource, Prompt
from pipelines.utils import find_first


class DAGSaver:
    def __init__(self, dag_root):
        self.nodes, self.edges = self.traverse_root(dag_root)
        node_names = [node.name for node in self.nodes]
        self.prompts = Prompt.objects.filter(name__in=node_names).all()
        self.builtins = BuiltinFunction.objects.filter(name__in=node_names).all()

    @classmethod
    def traverse_root(cls, root):
        nodes = []
        edges = []

        def traverse(node):
            nodes.append(node)
            for edge in node.edges:
                edges.append(edge)
                traverse(edge.target)

        traverse(root)
        return nodes, edges

    def save(self, pipeline: PipelineSource, update: bool = False):
        if update:
            pipeline.delete_dependents()

        dag_nodes = self.create_dag_nodes(pipeline)
        self.create_dag_edges(dag_nodes)

    def create_dag_nodes(self, pipeline):
        dag_nodes = [
            DAGNode(
                identifier=node.identifier,
                name=node.name,
                type=self.get_dag_node_type(node.name),
                pipeline_source=pipeline,
            )
            for node in self.nodes
        ]

        if dag_nodes:
            DAGNode.objects.bulk_create(dag_nodes)
        return dag_nodes

    def create_dag_edges(self, dag_nodes):
        edges = [
            DAGEdge(
                from_node=find_first(
                    lambda n: n.name == edge.source.name
                    and n.identifier == edge.source.identifier,
                    dag_nodes,
                ),
                to_node=find_first(
                    lambda n: n.name == edge.target.name
                    and n.identifier == edge.target.identifier,
                    dag_nodes,
                ),
            )
            for edge in self.edges
        ]

        if edges:
            DAGEdge.objects.bulk_create(edges)

    def get_dag_node_type(self, node_name):
        prompt = find_first(lambda p: p.name == node_name, self.prompts)
        builtin = find_first(lambda p: p.name == node_name, self.builtins)

        if prompt is not None:
            dag_node_type = TypesOfDAGNodes.PROMPT
        elif builtin is not None:
            dag_node_type = TypesOfDAGNodes.BUILTIN_FUNCTION
        else:
            dag_node_type = TypesOfDAGNodes.PLACEHOLDER

        return dag_node_type
