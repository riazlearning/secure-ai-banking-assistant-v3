from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=4000,
    )

    thread_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    thread_id: str
