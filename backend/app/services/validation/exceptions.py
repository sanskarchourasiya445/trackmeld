"""Custom exceptions for schedule validation and approval gate checks."""


class ValidationException(Exception):
    """Base exception for validation errors."""
    pass


class ValidationExecutionError(ValidationException):
    """Raised when validation execution fails due to corrupt inputs or internal errors."""
    pass


class ScheduleApprovalBlockedError(ValidationException):
    """Raised when an un-approvable schedule attempts to pass the approval gate."""
    def __init__(self, message: str, status: str, error_count: int) -> None:
        super().__init__(message)
        self.status = status
        self.error_count = error_count
