"""Explicit operational error types."""


class AgentOperationalError(Exception):
    """Base operational error."""


class TransientProviderError(AgentOperationalError):
    """A provider failure that may succeed on retry."""


class PermanentProviderError(AgentOperationalError):
    """A provider failure that should not be retried."""


class ProviderTimeout(AgentOperationalError):
    """The provider exceeded the attempt timeout contract."""


class CircuitOpenError(AgentOperationalError):
    """The dependency circuit breaker is open."""


class BudgetExceeded(AgentOperationalError):
    """The request exceeded a configured resource budget."""


class RequestDeadlineExceeded(AgentOperationalError):
    """The complete request exceeded its deadline."""
