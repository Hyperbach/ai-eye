class PipelineException(Exception):
    def __init__(self, msg=None):
        self.msg = "Generic Pipeline Exception" if msg is None else msg

    def __str__(self):
        return self.msg


class InvalidFunctionNameError(PipelineException):
    def __init__(self, msg):
        super().__init__(msg)


class NoDAGNodesError(PipelineException):
    def __init__(self, msg):
        super().__init__(msg)


class UnableToDetermineRootError(PipelineException):
    def __init__(self, msg):
        super().__init__(msg)


class CallBuiltinFunctionError(PipelineException):
    def __init__(self, msg):
        super().__init__(msg)


class CallPromptError(PipelineException):
    def __init__(self, msg):
        super().__init__(msg)


class InvalidArgumentsError(PipelineException):
    def __init__(self, msg):
        super().__init__(msg)
