"""Custom exceptions for the vsensor package."""


class VSensorError(Exception):
    """Base class for all VSensor related errors."""


class TransportError(VSensorError):
    """Communication error in the transport layer."""


class TimeoutError(TransportError):
    """Raised when a transport operation times out."""
