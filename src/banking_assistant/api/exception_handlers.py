from fastapi import Request
from fastapi.responses import JSONResponse

from banking_assistant.domain.exceptions import TransferRejectedError


async def transfer_rejected_handler(
    request: Request,
    exc: TransferRejectedError,
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
