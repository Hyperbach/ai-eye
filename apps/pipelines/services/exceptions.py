class PipelineException(Exception):
    def __init__(self, msg):
        super().__init__(f"Pipeline Exception: {msg}")


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
    def __init__(self, fn_name):
        super().__init__(
            msg=f"Neither a built-in function nor a prompt with the name '{fn_name}' could be determined."
        )


class FunctionsManagerException(Exception):
    def __init__(self, msg):
        super().__init__(f"FunctionsManagerException: {msg}")


class LoadModuleError(FunctionsManagerException):
    pass


class UserDefinedFunctionsError(FunctionsManagerException):
    pass
