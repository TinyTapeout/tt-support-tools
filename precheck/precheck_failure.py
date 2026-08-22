class PrecheckFailure(Exception):
    pass


class PrecheckWarning(Exception):
    pass


class PrecheckFailureGroup(ExceptionGroup):
    pass


class PrecheckWarningGroup(ExceptionGroup):
    pass
