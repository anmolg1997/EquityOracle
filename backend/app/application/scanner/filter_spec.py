"""FilterSpec builder — translates scanning criteria into executable filters.

Inspired by stock-screener's pattern of declarative filter definitions
that can be translated to SQL or in-memory evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class FilterOperator(str, Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    BETWEEN = "between"
    ABOVE_PCT = "above_pct"
    WITHIN_PCT = "within_pct"
    NEAR = "near"
    TRENDING_UP = "trending_up"


@dataclass
class FilterCriteria:
    field: str
    operator: FilterOperator
    value: Any = None
    reference: str | None = None
    min_value: Any = None
    max_value: Any = None
    multiplier: float = 1.0
    periods: int = 0


@dataclass
class FilterSpec:
    """A set of filter criteria that defines a scan."""

    name: str = ""
    description: str = ""
    criteria: list[FilterCriteria] = field(default_factory=list)

    def add(
        self,
        field_name: str,
        operator: str,
        value: Any = None,
        reference: str | None = None,
        **kwargs: Any,
    ) -> "FilterSpec":
        self.criteria.append(
            FilterCriteria(
                field=field_name,
                operator=FilterOperator(operator),
                value=value,
                reference=reference,
                min_value=kwargs.get("min"),
                max_value=kwargs.get("max"),
                multiplier=kwargs.get("multiplier", 1.0),
                periods=kwargs.get("periods", 0),
            )
        )
        return self

    def evaluate(self, data: dict[str, Any]) -> bool:
        """Evaluate all criteria against a data dict. Returns True if all pass."""
        return all(self._evaluate_single(c, data) for c in self.criteria)

    def _evaluate_single(self, criteria: FilterCriteria, data: dict[str, Any]) -> bool:
        field_val = data.get(criteria.field)
        if field_val is None:
            return False

        compare_val = criteria.value
        if criteria.reference:
            compare_val = data.get(criteria.reference)
            if compare_val is None:
                return False
            if criteria.multiplier != 1.0:
                compare_val = float(compare_val) * criteria.multiplier

        field_val = float(field_val)

        match criteria.operator:
            case FilterOperator.GT:
                return field_val > float(compare_val)
            case FilterOperator.GTE:
                return field_val >= float(compare_val)
            case FilterOperator.LT:
                return field_val < float(compare_val)
            case FilterOperator.LTE:
                return field_val <= float(compare_val)
            case FilterOperator.EQ:
                return field_val == float(compare_val)
            case FilterOperator.BETWEEN:
                return (
                    criteria.min_value is not None
                    and criteria.max_value is not None
                    and float(criteria.min_value) <= field_val <= float(criteria.max_value)
                )
            case FilterOperator.ABOVE_PCT:
                ref = float(data.get(criteria.reference, 0))
                return ref > 0 and ((field_val - ref) / ref * 100) >= float(criteria.value)
            case FilterOperator.WITHIN_PCT:
                ref = float(data.get(criteria.reference, 0))
                return ref > 0 and ((ref - field_val) / ref * 100) <= float(criteria.value)
            case _:
                return True
