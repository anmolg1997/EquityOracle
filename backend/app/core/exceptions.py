"""Base exception hierarchy for EquityOracle."""

from __future__ import annotations


class EquityOracleError(Exception):
    """Root exception — all application errors inherit from this."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


# --- Data Layer ---


class DataProviderError(EquityOracleError):
    """A market data provider failed or returned invalid data."""


class DataFreshnessError(DataProviderError):
    """Data is stale beyond the acceptable threshold."""


class DataQualityError(DataProviderError):
    """Data failed quality gate validation."""


class ProviderUnavailableError(DataProviderError):
    """All providers in the fallback chain are unavailable."""


# --- Domain ---


class DomainError(EquityOracleError):
    """Violation of a domain invariant."""


class InsufficientDataError(DomainError):
    """Not enough historical data to compute indicators or features."""


class LiquidityError(DomainError):
    """Stock fails minimum liquidity requirements."""


# --- Portfolio ---


class PortfolioError(EquityOracleError):
    """Portfolio-related errors."""


class OrderRejectedError(PortfolioError):
    """Order rejected by risk manager or circuit breaker."""


class CircuitBreakerTrippedError(PortfolioError):
    """Circuit breaker is in a non-GREEN state, blocking the action."""


# --- ML ---


class MLError(EquityOracleError):
    """ML pipeline errors."""


class LookaheadBiasError(MLError):
    """Feature uses data not yet available at the prediction timestamp."""


class OverfittingDetectedError(MLError):
    """Model shows signs of overfitting during validation."""


# --- Infrastructure ---


class ConfigurationError(EquityOracleError):
    """Invalid or missing configuration."""
