"""Simple interest calculations independent of agent tooling."""

from decimal import Decimal, DecimalException
import logging
from banking_assistant.services.exceptions import InvalidInterestInputError, CalculationError

logger = logging.getLogger(__name__)


class InterestService:
    def calculate_simple_interest(
        self, principal: Decimal, annual_rate: Decimal, years: Decimal,
    ) -> Decimal:
        """Return P × R × T / 100; rate is a percentage and time is in years."""
        logger.info(
            "Calculating simple interest",
            extra={"principal": str(principal), "annual_rate": str(annual_rate), "years": str(years)},
        )
        for name, value in (
            ("principal", principal), ("annual_rate", annual_rate), ("years", years),
        ):
            if not value.is_finite() or value < 0:
                logger.warning("Invalid simple interest input", extra={"field": name})
                raise InvalidInterestInputError(f"{name} must be a finite, non-negative number")
        try:
            interest = principal * annual_rate * years / Decimal("100")
        except DecimalException as exc:
            raise CalculationError("Unable to calculate simple interest") from exc
        logger.info("Simple interest calculated", extra={"simple_interest": str(interest)})
        return interest
