class PipelineException(Exception):
    def __init__(self, msg):
        super().__init__("Pipeline Exception: " + msg)


class InvalidFunctionNameError(PipelineException):
    pass


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
