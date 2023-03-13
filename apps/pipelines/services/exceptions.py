class PipelineException(Exception):
    def __init__(self, msg):
        super().__init__("Pipeline Exception: " + msg)


class NoDAGNodesError(PipelineException):
    pass


class UnableToDetermineRootError(PipelineException):
    pass


class CallBuiltinFunctionError(PipelineException):
    pass


class CallPromptError(PipelineException):
    pass


class InvalidArgumentsError(PipelineException):
    pass


class UnableToDetermineFunctionError(PipelineException):
    def __init__(self, name):
        super().__init__(
            msg=f"Neither a built-in function nor a prompt with the name '{name}' could be determined."
        )
