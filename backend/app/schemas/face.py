"""
Pydantic schemas for Face Registration and Authentication endpoints.
"""

from pydantic import BaseModel, Field


class FaceRegisterResponse(BaseModel):
    success: bool = Field(
        default=True, 
        description="Operation success status", 
        json_schema_extra={"example": True}
    )
    message: str = Field(
        default="Face registered successfully", 
        description="Human-readable status message", 
        json_schema_extra={"example": "Face registered successfully"}
    )


class FaceVerifyResponse(BaseModel):
    success: bool = Field(
        default=True, 
        description="Operation execution status", 
        json_schema_extra={"example": True}
    )
    verified: bool = Field(
        ..., 
        description="Whether the face verification matched the registered biometric profile", 
        json_schema_extra={"example": True}
    )
    match_score: float = Field(
        ..., 
        description="User-friendly normalized similarity score on a 0-100 scale (not an identity probability)", 
        json_schema_extra={"example": 96.4}
    )
    similarity: float = Field(
        ..., 
        description="Raw cosine similarity score in range [-1.0, 1.0]", 
        json_schema_extra={"example": 0.928}
    )
    message: str = Field(
        ..., 
        description="Human-readable verification result message", 
        json_schema_extra={"example": "Face verification successful"}
    )

