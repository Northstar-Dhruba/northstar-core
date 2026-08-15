"""Domain validation errors for the foundation package."""


class ValidationError(ValueError):
    """Base exception for invalid domain values."""


class InvalidSymbolError(ValidationError):
    """Raised when a symbol value is invalid."""


class InvalidCurrencyError(ValidationError):
    """Raised when a currency value is invalid."""


class InvalidExchangeCodeError(ValidationError):
    """Raised when an exchange code value is invalid."""


class InvalidQuantityError(ValidationError):
    """Raised when a quantity value is invalid."""


class InvalidPercentageError(ValidationError):
    """Raised when a percentage value is invalid."""
