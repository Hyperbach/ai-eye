from lark import Lark, Transformer, v_args

GRAMMAR = """
    start: func_invocation
    expression: name | func_invocation
    name: /[a-zA-Z][a-zA-Z_0-9]*/
    func_invocation: name "(" func_args? ")"
    func_args: func_arg ("," func_arg)*
    func_arg: arg_assign | expression
    arg_assign: name "=" expression
    %import common.WS
    %ignore WS
"""


class Node:
    last_id = 0

    def __init__(self, name):
        self.name = name
        self.id = Node.last_id
        self.edges = []
        Node.last_id += 1

    def add_edge(self, edge):
        self.edges.append(edge)

    @property
    def full_name(self):
        return f"{self.name} {self.id}"

    @property
    def identifier(self):
        return self.id

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return self.full_name


class Edge:
    def __init__(self, source, target):
        self.source = source
        self.target = target

    @property
    def full_name(self):
        return f"{self.source} -> {self.target}"

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return self.full_name


class DAGBuilder(Transformer):
    @v_args(inline=True)
    def name(self, name):
        return Node(name.value)

    @v_args(inline=True)
    def func_invocation(self, name, *args):
        node = name
        for arg in args:
            if isinstance(arg, Node):
                edge = Edge(node, arg)
                node.add_edge(edge)
            else:
                for nested_arg in arg:
                    # arg_assign
                    if isinstance(nested_arg, tuple):
                        arg_name, arg_value = nested_arg
                        # create a new node with the name of the argument
                        arg_node = arg_name
                        # add an edge from the function node to the argument node
                        edge = Edge(node, arg_node)
                        node.add_edge(edge)
                        # add an edge from the argument node to the argument value
                        edge = Edge(arg_node, arg_value)
                        arg_node.add_edge(edge)
                    else:
                        edge = Edge(node, nested_arg)
                        node.add_edge(edge)
        return node

    def func_args(self, *args):
        return args[0]

    def func_arg(self, value):
        return value[0]

    @v_args(inline=True)
    def start(self, *args):
        return args[0]

    @v_args(inline=True)
    def expression(self, *args):
        return args[0]

    @v_args(inline=True)
    def arg_assign(self, name, value):
        return name, value

    def build(self, expr):
        parser = Lark(GRAMMAR, parser="lalr", transformer=self)
        return parser.parse(expr)
