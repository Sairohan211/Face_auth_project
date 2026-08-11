import re
from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class UserRegisterRequest(BaseModel):
    full_name: str = Field(
        ..., 
        min_length=1, 
        description="Full name of the user", 
        json_schema_extra={"example": "Jane Doe"}
    )
    email: str = Field(
        ..., 
        description="A valid email address", 
        json_schema_extra={"example": "jane.doe@example.com"}
    )
    password: str = Field(
        ..., 
        min_length=8, 
        description="Password (minimum 8 characters)", 
        json_schema_extra={"example": "SecurePassword123!"}
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Full name cannot be empty or just whitespace.")
        return stripped

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Invalid email format.")
        return cleaned

class UserRegisterResponse(BaseModel):
    success: bool = Field(
        ..., 
        description="Operation success status", 
        json_schema_extra={"example": True}
    )
    message: str = Field(
        ..., 
        description="Human-readable status message", 
        json_schema_extra={"example": "Account created successfully. A verification code has been sent to your email."}
    )
    user_id: str = Field(
        ..., 
        description="UUID of the newly created user", 
        json_schema_extra={"example": "d44d56a6-a00c-4d4d-b434-be8a586f16ae"}
    )
    email: str = Field(
        ...,
        description="Email address of the newly registered user",
        json_schema_extra={"example": "jane.doe@example.com"}
    )
    access_token: str | None = Field(
        default=None,
        description="JWT access token for immediate session"
    )
    token_type: str | None = Field(
        default="bearer",
        description="Token type"
    )

class VerifyEmailRequest(BaseModel):
    email: str = Field(
        ...,
        description="User email address",
        json_schema_extra={"example": "jane.doe@example.com"}
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit numeric OTP code",
        json_schema_extra={"example": "123456"}
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Invalid email format.")
        return cleaned

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) != 6 or not cleaned.isdigit():
            raise ValueError("OTP code must be exactly 6 numeric digits.")
        return cleaned

class VerifyEmailResponse(BaseModel):
    success: bool = Field(default=True, description="Verification success status")
    message: str = Field(
        default="Email verified successfully. You may now proceed to face registration.",
        description="Human-readable status message"
    )

class ResendOtpRequest(BaseModel):
    email: str = Field(
        ...,
        description="User email address",
        json_schema_extra={"example": "jane.doe@example.com"}
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Invalid email format.")
        return cleaned

class ResendOtpResponse(BaseModel):
    success: bool = Field(default=True, description="Resend status")
    message: str = Field(
        default="A new verification code has been sent.",
        description="Human-readable status message"
    )

class UserLoginRequest(BaseModel):
    email: str = Field(
        ..., 
        description="A valid email address", 
        json_schema_extra={"example": "jane.doe@example.com"}
    )
    password: str = Field(
        ..., 
        min_length=1, 
        description="Account password", 
        json_schema_extra={"example": "SecurePassword123!"}
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned or not EMAIL_REGEX.match(cleaned):
            raise ValueError("Invalid email format.")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value:
            raise ValueError("Password cannot be empty.")
        return value

class SessionInfo(BaseModel):
    access_token: str = Field(..., description="Supabase JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int | None = Field(default=None, description="Token lifetime in seconds")
    expires_at: int | None = Field(default=None, description="Unix timestamp of token expiration")
    refresh_token: str | None = Field(default=None, description="Supabase refresh token")

class UserLoginResponse(BaseModel):
    success: bool = Field(default=True, description="Operation success status")
    message: str = Field(default="Login successful", description="Human-readable status message")
    user_id: str = Field(..., description="UUID of the authenticated user")
    access_token: str = Field(..., description="Supabase JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int | None = Field(default=None, description="Token lifetime in seconds")
    refresh_token: str | None = Field(default=None, description="Supabase refresh token")
    email_verified: bool = Field(default=False, description="Application-level email verification status")
    session: SessionInfo | None = Field(default=None, description="Detailed session object")

class UserProfileResponse(BaseModel):
    id: str = Field(..., description="UUID of the user")
    full_name: str = Field(..., description="Full name of the user")
    email: str = Field(..., description="Email address from profile")
    email_verified: bool = Field(default=False, description="Email verification status")
    created_at: str | None = Field(default=None, description="Timestamp of profile creation")

