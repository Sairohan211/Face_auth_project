"""
Face Verification Service.

Handles face biometric verification by comparing a freshly submitted face photograph
against the authenticated user's registered 512-D embedding stored in public.face_embeddings.
"""

import logging
from typing import Any, Dict, List, Optional, Union
import numpy as np

from app.core.config import settings
from app.core.supabase import supabase
from app.services.face_recognition import (
    FaceRecognitionService,
    face_service,
    FaceRecognitionError,
    NoFaceDetectedError,
    MultipleFacesDetectedError,
    InvalidImageError,
)

logger = logging.getLogger(__name__)


class NoRegisteredFaceError(FaceRecognitionError):
    """Raised when no registered face embedding exists for the user."""
    pass


class FaceVerificationService:
    def __init__(self, recognition_service: Optional[FaceRecognitionService] = None):
        self.recognition_service = recognition_service or face_service

    @staticmethod
    def _parse_stored_embedding(raw_embedding: Union[List[Any], str]) -> List[float]:
        """
        Parses the pgvector embedding from Supabase response into a list of floats.
        Handles both JSON lists and pgvector string format '[0.01, -0.02, ...]'.
        """
        if isinstance(raw_embedding, list):
            return [float(x) for x in raw_embedding]
        elif isinstance(raw_embedding, str):
            cleaned = raw_embedding.strip("[]").split(",")
            return [float(x.strip()) for x in cleaned if x.strip()]
        raise ValueError(f"Unrecognized embedding format: {type(raw_embedding)}")

    @staticmethod
    def calculate_match_score(similarity: float) -> float:
        """
        Converts cosine similarity [-1.0, 1.0] into a user-friendly normalized score [0.0, 100.0].
        
        NOTE: This match_score is a normalized similarity score for UI presentation,
        NOT a statistical probability that the person is the claimed identity.
        """
        normalized = ((similarity + 1.0) / 2.0) * 100.0
        clamped = max(0.0, min(100.0, normalized))
        return round(clamped, 1)

    async def verify_face(
        self,
        user_id: str,
        image_bytes: bytes,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Extracts the 512-D face embedding from raw image bytes and compares it against
        the user's registered embedding in public.face_embeddings.

        Security & Privacy Guarantees:
        - The uploaded verification image is processed strictly in memory and never stored.
        - The newly generated verification embedding is never stored or persisted.
        - Neither embeddings nor raw image bytes are logged.
        - The user ID is strictly determined from the authenticated context.
        """
        if not image_bytes:
            raise InvalidImageError("No image data provided.")

        # 1. Retrieve the registered face embedding for this authenticated user only
        try:
            record_response = (
                supabase.table("face_embeddings")
                .select("embedding")
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as db_err:
            logger.error("Database query error retrieving face embedding for user %s: %s", user_id, db_err)
            raise RuntimeError("Database error occurred while retrieving registered face embedding.") from db_err

        if not record_response.data or len(record_response.data) == 0:
            logger.warning("No registered face embedding record found for user %s", user_id)
            raise NoRegisteredFaceError("No registered face biometric profile found for this user.")

        raw_stored_embedding = record_response.data[0].get("embedding")
        if not raw_stored_embedding:
            raise NoRegisteredFaceError("Registered face embedding is empty or invalid.")

        registered_embedding = self._parse_stored_embedding(raw_stored_embedding)
        if len(registered_embedding) != 512:
            logger.error("Stored embedding for user %s has invalid dimension: %d", user_id, len(registered_embedding))
            raise RuntimeError("Stored face biometric profile has invalid dimensionality.")

        # 2. Extract 512-D normalized embedding from newly captured verification image
        # This will raise NoFaceDetectedError, MultipleFacesDetectedError, or InvalidImageError if invalid
        verification_embedding: List[float] = self.recognition_service.extract_single_face_embedding(image_bytes)

        # 3. Compute cosine similarity between registered embedding and newly captured embedding
        similarity = self.recognition_service.compute_similarity(registered_embedding, verification_embedding)

        # 4. Compare against configurable threshold
        match_threshold = threshold if threshold is not None else settings.FACE_MATCH_THRESHOLD
        verified = bool(similarity >= match_threshold)

        # 5. Convert to normalized match score
        match_score = self.calculate_match_score(similarity)

        message = "Face verification successful" if verified else "Face verification failed"

        logger.info(
            "Face verification performed for user %s: verified=%s, match_score=%.1f",
            user_id,
            verified,
            match_score
        )

        return {
            "success": True,
            "verified": verified,
            "match_score": match_score,
            "similarity": round(float(similarity), 4),
            "message": message,
        }


face_verification_service = FaceVerificationService()
