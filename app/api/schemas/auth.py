from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,30}$", examples=["an_nguyen"])
    password: str = Field(min_length=8, max_length=72, examples=["matkhau123"])

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, password: str) -> str:
        if len(password.encode()) > 72:
            raise ValueError("must be at most 72 bytes")
        return password


class LoginRequest(BaseModel):
    username: str = Field(max_length=30, examples=["an_nguyen"])
    password: str = Field(max_length=72, examples=["matkhau123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(description="Seconds until the token expires", examples=[3600])
