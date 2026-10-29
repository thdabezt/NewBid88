from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str = Field(examples=["VALIDATION_ERROR"])
    message: str = Field(examples=["password: String should have at least 8 characters"])
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
