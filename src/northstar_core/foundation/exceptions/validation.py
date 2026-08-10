"""Domain validation errors for the foundation package."""


class ValidationError(ValueError):
    """Base exception for invalid domain values."""


class InvalidSymbolError(ValidationError):
    """Raised when a symbol value is invalid."""
