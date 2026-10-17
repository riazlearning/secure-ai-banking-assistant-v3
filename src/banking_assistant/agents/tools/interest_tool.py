from decimal import Decimal
import logging

from langchain_core.tools import tool, ToolException
from pydantic import BaseModel, Field

from banking_assistant.services.interest_service import InterestService
from banking_assistant.services.exceptions import InvalidInterestInputError

logger = logging.getLogger(__name__)


class SimpleInterestInput(BaseModel):
    principal: float = Field(ge=0, allow_inf_nan=False, description="Initial amount")
    annual_rate: float = Field(
        ge=0,
        allow_inf_nan=False,
        description="Annual percentage rate, e.g. 5 for 5%",
    )
    years: float = Field(
        ge=0,
        allow_inf_nan=False,
        description="Duration in years; 6 months is 0.5 years",
    )


@tool(args_schema=SimpleInterestInput)
def calculate_simple_interest(
    principal: float, annual_rate: float, years: float
) -> dict[str, str]:
    """Calculate simple interest and total amount from principal, annual percent rate, and years.

    This calculation does not compound interest or execute any banking transaction.
    """
    logger.info("Simple interest tool invoked")
    amount = Decimal(str(principal))
    try:
        interest = InterestService().calculate_simple_interest(
            amount,
            Decimal(str(annual_rate)),
            Decimal(str(years)),
        )
    except InvalidInterestInputError as exc:
        raise ToolException(str(exc)) from exc
    except Exception:
        logger.exception("Simple interest tool failed")
        raise
    result = {
        "simple_interest": format(interest, "f"),
        "total_amount": format(amount + interest, "f"),
    }
    logger.info("Simple interest tool completed", extra=result)
    return result
