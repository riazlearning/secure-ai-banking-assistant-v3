from fastapi import Request
from fastapi.responses import JSONResponse

from banking_assistant.domain.exceptions import TransferRejectedError
import logging
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from banking_assistant.agents.exceptions import AgentError, LLMError, LLMTimeoutError
from banking_assistant.services.exceptions import ApplicationError, InvalidInterestInputError, MissingAnswerError

logger = logging.getLogger(__name__)


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


async def application_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Request failed", exc_info=(type(exc), exc, exc.__traceback__), extra={"path": request.url.path})
    if isinstance(exc, InvalidInterestInputError):
        return error_response(422, "INVALID_INTEREST_INPUT", str(exc))
    if isinstance(exc, LLMTimeoutError):
        return error_response(504, "LLM_TIMEOUT", "The language model timed out. Please try again.")
    if isinstance(exc, LLMError):
        return error_response(502, "LLM_UNAVAILABLE", "The language model is unavailable. Please try again.")
    if isinstance(exc, MissingAnswerError):
        return error_response(500, "MISSING_ANSWER", "Unable to generate an answer.")
    if isinstance(exc, AgentError):
        return error_response(500, "AGENT_EXECUTION_FAILED", "Unable to complete the request.")
    if isinstance(exc, ApplicationError):
        return error_response(500, "APPLICATION_ERROR", "Unable to complete the request.")
    return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")


async def request_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(422, "INVALID_REQUEST", "Request fields are missing or invalid.")


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    response = error_response(exc.status_code, "HTTP_ERROR", "The HTTP request could not be completed.")
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def transfer_rejected_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "TRANSFER_REJECTED",
                "message": str(exc),
            }
        },
    )
