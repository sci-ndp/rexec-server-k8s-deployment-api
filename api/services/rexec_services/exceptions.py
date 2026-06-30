"""
Exceptions raised by the Rexec service layer.
"""


class RexecConfigurationError(Exception):
    """Raised when the Rexec deployment configuration is invalid."""


class RexecValidationError(ValueError):
    """Raised when the request payload is invalid."""


class RexecDeploymentError(RuntimeError):
    """Raised when Kubernetes operations fail."""
