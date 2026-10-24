from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    # BR-01. Upper case is accepted here; the service stores the username in lower case.
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,30}$", examples=["an_nguyen"])
    password: str = Field(min_length=8, max_length=72, examples=["matkhau123"])

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, password: str) -> str:
        # bcrypt only reads the first 72 bytes, and an accented character takes more than one.
        if len(password.encode()) > 72:
            raise ValueError("must be at most 72 bytes")
        return password
