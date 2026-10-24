from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int = Field(examples=[7])
    username: str = Field(examples=["an_nguyen"])
    created_at: datetime
