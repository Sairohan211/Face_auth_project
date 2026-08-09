"""
Face Registration Service.

Handles face biometric enrollment by extracting local InsightFace 512-D embeddings
and managing user embedding records in public.face_embeddings.
"""

import logging
from typing import List, Optional
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


class FaceRegistrationService:
    def __init__(self, recognition_service: Optional[FaceRecognitionService] = None):
        self.recognition_service = recognition_service or face_service

    async def register_face(self, user_id: str, image_bytes: bytes) -> bool:
        """
        Extracts the 512-D face embedding from raw image bytes and registers/updates
        the user's record in public.face_embeddings.

        Security & Privacy Guarantees:
        - Raw face images are processed strictly in memory and never stored.
        - Embedding values and face images are never logged.
        - Exactly one active embedding record per user is maintained.
        """
        if not image_bytes:
            raise InvalidImageError("No image data provided.")

        # 1. Extract 512-D normalized embedding using local InsightFace model
        embedding: List[float] = self.recognition_service.extract_single_face_embedding(image_bytes)

        # 2. Update existing or insert new record in public.face_embeddings
        try:
            existing_record = (
                supabase.table("face_embeddings")
                .select("id")
                .eq("user_id", user_id)
                .execute()
            )

            if existing_record.data and len(existing_record.data) > 0:
                # Update existing record
                supabase.table("face_embeddings").update({
                    "embedding": embedding
                }).eq("user_id", user_id).execute()
                logger.info("Updated existing face embedding record for user %s", user_id)
            else:
                # Insert new record
                supabase.table("face_embeddings").insert({
                    "user_id": user_id,
                    "embedding": embedding
                }).execute()
                logger.info("Inserted new face embedding record for user %s", user_id)

            return True

        except Exception as db_err:
            logger.error("Database error saving face embedding for user %s: %s", user_id, db_err)
            raise RuntimeError("Database error occurred while persisting face embedding.") from db_err


face_registration_service = FaceRegistrationService()
