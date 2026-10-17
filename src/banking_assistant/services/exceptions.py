"""Application errors raised by services, independent of HTTP."""


class ApplicationError(Exception):
    pass


class InvalidInterestInputError(ApplicationError, ValueError):
    pass


class CalculationError(ApplicationError):
    pass


class MissingAnswerError(ApplicationError):
    pass
