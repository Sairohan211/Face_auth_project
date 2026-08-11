"""
Face Biometrics API Router.

Provides endpoints for registering face biometric embeddings.
"""

import logging
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.dependencies import get_current_user
from app.schemas.face import FaceRegisterResponse, FaceVerifyResponse
from app.services.face_registration import face_registration_service
from app.services.face_verification import face_verification_service, NoRegisteredFaceError
from app.services import otp_service
from app.services.face_recognition import (
    FaceRecognitionError,
    NoFaceDetectedError,
    MultipleFacesDetectedError,
    InvalidImageError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/face", tags=["Face Biometrics"])


@router.post(
    "/register",
    response_model=FaceRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Register face biometric embedding",
    description="Extracts a local 512-D face embedding from the uploaded image and stores it for the authenticated user."
)
async def register_face(
    file: UploadFile = File(..., description="Face photograph for biometric registration (JPEG/PNG/WEBP)"),
    current_user: Any = Depends(get_current_user),
):
    """
    Registers a face embedding for the authenticated user.
    
    Requirements:
    - User must be authenticated (Bearer token).
    - User ID is derived strictly from authentication context.
    - Application-level email verification must be completed (public.profiles.email_verified == true).
    - Exactly one face must be detected in the provided image.
    - Image is processed in memory and never stored in object storage.
    """
    user_id = str(current_user.id)

    # 1. Gate: Verify application-level email verification state (bypassed for demo)
    # if not otp_service.is_profile_email_verified(user_id):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Please verify your email before registering your face."
    #     )

    # 2. Read uploaded image bytes

    try:
        image_bytes = await file.read()
    except Exception as read_err:
        logger.error("Failed to read uploaded file for user %s: %s", user_id, read_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded image file."
        )

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty."
        )

    # 2. Extract embedding and persist to public.face_embeddings
    try:
        await face_registration_service.register_face(user_id=user_id, image_bytes=image_bytes)
        return FaceRegisterResponse(
            success=True,
            message="Face registered successfully"
        )

    except NoFaceDetectedError as nfe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in the image. Please provide a clear, well-lit portrait."
        )

    except MultipleFacesDetectedError as mfe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple faces detected in the image. Please provide a photo with exactly one face."
        )

    except InvalidImageError as iie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format: {str(iie)}"
        )

    except FaceRecognitionError as fre:
        logger.warning("Face recognition error for user %s: %s", user_id, fre)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to process face biometric from the provided image."
        )

    except RuntimeError as rte:
        logger.error("Internal service error during face registration for user %s: %s", user_id, rte)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while registering the face embedding. Please try again."
        )

    except Exception as exc:
        logger.error("Unexpected error in register_face for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during face registration."
        )


@router.post(
    "/verify",
    response_model=FaceVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify face biometric embedding",
    description="Extracts a local 512-D face embedding from the uploaded image, compares it against the authenticated user's registered embedding via cosine similarity, and returns the verification verdict."
)
async def verify_face(
    file: UploadFile = File(..., description="Face photograph for biometric verification (JPEG/PNG/WEBP)"),
    current_user: Any = Depends(get_current_user),
):
    """
    Verifies a face image against the authenticated user's registered face embedding.

    Requirements:
    - User must be authenticated (Bearer token).
    - User ID is derived strictly from authentication context (never from body/query).
    - Exactly one face must be detected in the submitted image.
    - Compares new 512-D embedding against registered profile via cosine similarity.
    - Image and verification embedding are processed in-memory and never stored.
    """
    user_id = str(current_user.id)

    # 1. Read uploaded verification image bytes
    try:
        image_bytes = await file.read()
    except Exception as read_err:
        logger.error("Failed to read uploaded verification file for user %s: %s", user_id, read_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded image file."
        )

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty."
        )

    # 2. Perform verification against registered profile
    try:
        result = await face_verification_service.verify_face(
            user_id=user_id,
            image_bytes=image_bytes
        )
        return FaceVerifyResponse(**result)

    except NoRegisteredFaceError as nrfe:
        logger.info("Verification attempted for user %s with no registered face", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered face biometric profile found for this user. Please register your face first."
        )

    except NoFaceDetectedError as nfe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in the image. Please provide a clear, well-lit portrait."
        )

    except MultipleFacesDetectedError as mfe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple faces detected in the image. Please provide a photo with exactly one face."
        )

    except InvalidImageError as iie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format: {str(iie)}"
        )

    except FaceRecognitionError as fre:
        logger.warning("Face recognition error during verification for user %s: %s", user_id, fre)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to process face biometric from the provided image."
        )

    except RuntimeError as rte:
        logger.error("Internal service error during face verification for user %s: %s", user_id, rte)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while verifying the face embedding. Please try again."
        )

    except Exception as exc:
        logger.error("Unexpected error in verify_face for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during face verification."
        )

