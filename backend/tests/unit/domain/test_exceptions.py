"""Tests for custom exception hierarchy."""

import pytest

from app.core.exceptions import (
    CircuitBreakerTrippedError,
    ConfigurationError,
    DataFreshnessError,
    DataProviderError,
    DataQualityError,
    DomainError,
    EquityOracleError,
    InsufficientDataError,
    LiquidityError,
    LookaheadBiasError,
    MLError,
    OrderRejectedError,
    OverfittingDetectedError,
    PortfolioError,
    ProviderUnavailableError,
)


class TestExceptionHierarchy:
    def test_root_exception(self):
        err = EquityOracleError("test", details={"key": "val"})
        assert str(err) == "test"
        assert err.details == {"key": "val"}

    def test_data_provider_inherits_root(self):
        err = DataProviderError("provider failed")
        assert isinstance(err, EquityOracleError)

    def test_data_freshness_inherits_provider(self):
        err = DataFreshnessError("stale data")
        assert isinstance(err, DataProviderError)
        assert isinstance(err, EquityOracleError)

    def test_data_quality_inherits_provider(self):
        assert issubclass(DataQualityError, DataProviderError)

    def test_provider_unavailable(self):
        assert issubclass(ProviderUnavailableError, DataProviderError)

    def test_domain_error(self):
        assert issubclass(InsufficientDataError, DomainError)
        assert issubclass(LiquidityError, DomainError)

    def test_portfolio_errors(self):
        assert issubclass(OrderRejectedError, PortfolioError)
        assert issubclass(CircuitBreakerTrippedError, PortfolioError)
        assert issubclass(PortfolioError, EquityOracleError)

    def test_ml_errors(self):
        assert issubclass(LookaheadBiasError, MLError)
        assert issubclass(OverfittingDetectedError, MLError)
        assert issubclass(MLError, EquityOracleError)

    def test_config_error(self):
        assert issubclass(ConfigurationError, EquityOracleError)

    def test_details_default_empty(self):
        err = EquityOracleError("test")
        assert err.details == {}

    def test_can_catch_by_hierarchy(self):
        with pytest.raises(EquityOracleError):
            raise LookaheadBiasError("lookahead detected")
