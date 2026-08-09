"""
Local Face Recognition Service using InsightFace and ONNX Runtime.

This module provides local, CPU-based face detection and ArcFace feature embedding
generation for biometric authentication. No external/cloud APIs are called.

License Note:
- InsightFace pre-trained models (buffalo_l) are intended for non-commercial,
  research, and educational purposes.
"""

import base64
import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

try:
    from insightface.app import FaceAnalysis
except ImportError:
    FaceAnalysis = None

logger = logging.getLogger(__name__)


class FaceRecognitionError(Exception):
    """Base exception for face recognition errors."""
    pass


class InvalidImageError(FaceRecognitionError):
    """Raised when an input image cannot be decoded or is empty."""
    pass


class NoFaceDetectedError(FaceRecognitionError):
    """Raised when zero faces are detected in an image."""
    pass


class MultipleFacesDetectedError(FaceRecognitionError):
    """Raised when multiple faces are detected where exactly one is required."""
    def __init__(self, count: int, message: Optional[str] = None):
        self.count = count
        super().__init__(message or f"Expected 1 face, but detected {count} faces in image.")


class FaceRecognitionService:
    """
    Local Face Recognition Service using InsightFace ArcFace models via ONNX Runtime.
    """

    def __init__(
        self,
        model_name: str = "buffalo_l",
        det_size: Tuple[int, int] = (640, 640),
        providers: Optional[List[str]] = None,
        allowed_modules: Optional[List[str]] = None,
    ):
        """
        Initialize the FaceRecognitionService.

        :param model_name: Name of the InsightFace model pack (default: 'buffalo_l')
        :param det_size: Input size tuple for face detector (default: (640, 640))
        :param providers: ONNX Runtime execution providers (default: ['CPUExecutionProvider'])
        :param allowed_modules: Specific modules to load (default: ['detection', 'recognition'])
        """
        self.model_name = model_name
        self.det_size = det_size
        self.providers = providers or ["CPUExecutionProvider"]
        self.allowed_modules = allowed_modules or ["detection", "recognition"]
        self._app: Optional[Any] = None

    def _get_app(self) -> Any:
        """Lazily initialize and return the FaceAnalysis app instance."""
        if self._app is None:
            if FaceAnalysis is None:
                raise FaceRecognitionError("InsightFace is not installed in the current environment.")

            logger.info("Initializing InsightFace model pack '%s' with ONNX Runtime...", self.model_name)
            app = FaceAnalysis(
                name=self.model_name,
                providers=self.providers,
                allowed_modules=self.allowed_modules
            )
            # Prepare detector with ctx_id=0 for CPU / execution provider
            app.prepare(ctx_id=0, det_size=self.det_size)
            self._app = app
            logger.info("InsightFace model pack '%s' ready.", self.model_name)
        return self._app

    def decode_image(self, image_input: Union[np.ndarray, bytes, str, Path]) -> np.ndarray:
        """
        Decode various image input formats into an OpenCV BGR numpy ndarray.

        Supports:
        - np.ndarray (already BGR or RGB image)
        - bytes (raw image bytes: JPEG, PNG, WEBP)
        - str (base64 string, base64 data URI, or filesystem path)
        - Path (filesystem path)
        """
        if isinstance(image_input, np.ndarray):
            if image_input.size == 0:
                raise InvalidImageError("Input numpy array is empty.")
            return image_input

        if isinstance(image_input, (str, Path)):
            str_path = str(image_input)
            # Check if it's a base64 string
            if str_path.startswith("data:image/") or ";base64," in str_path:
                try:
                    _, encoded = str_path.split(";base64,", 1)
                    image_bytes = base64.b64decode(encoded)
                    return self._decode_bytes_to_bgr(image_bytes)
                except Exception as e:
                    raise InvalidImageError(f"Failed to decode base64 data URI: {e}") from e

            # Check if it's a filesystem path
            path = Path(str_path)
            if path.exists() and path.is_file():
                img = cv2.imread(str(path))
                if img is None:
                    raise InvalidImageError(f"Failed to read image file from path: {str_path}")
                return img

            # Try raw base64 string
            try:
                image_bytes = base64.b64decode(str_path)
                return self._decode_bytes_to_bgr(image_bytes)
            except Exception:
                raise InvalidImageError("Input string is neither a valid file path nor valid base64 image data.")

        if isinstance(image_input, bytes):
            return self._decode_bytes_to_bgr(image_input)

        raise InvalidImageError(f"Unsupported image input type: {type(image_input)}")

    def _decode_bytes_to_bgr(self, image_bytes: bytes) -> np.ndarray:
        """Decodes raw byte array into OpenCV BGR numpy array using Pillow + OpenCV."""
        if not image_bytes:
            raise InvalidImageError("Image bytes are empty.")

        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            # Convert to RGB mode (handles RGBA, grayscale, CMYK, etc.)
            rgb_img = pil_img.convert("RGB")
            np_rgb = np.array(rgb_img)
            # Convert RGB to BGR for OpenCV / InsightFace
            bgr_img = cv2.cvtColor(np_rgb, cv2.COLOR_RGB2BGR)
            return bgr_img
        except Exception as e:
            raise InvalidImageError(f"Unable to parse image bytes: {e}") from e

    def detect_faces(self, image_input: Union[np.ndarray, bytes, str, Path]) -> List[Dict[str, Any]]:
        """
        Detect all faces in the provided image and generate their embeddings.

        :param image_input: Image in any supported format (path, bytes, ndarray, base64)
        :return: List of dicts with keys: 'bbox', 'kps', 'det_score', 'embedding'
        """
        bgr_image = self.decode_image(image_input)
        app = self._get_app()

        raw_faces = app.get(bgr_image)
        results: List[Dict[str, Any]] = []

        for face in raw_faces:
            embedding = face.embedding
            norm_embedding = None
            if embedding is not None:
                # Compute L2 normalized embedding
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    norm_embedding = (embedding / norm).astype(float).tolist()
                else:
                    norm_embedding = embedding.astype(float).tolist()

            results.append({
                "bbox": face.bbox.tolist() if hasattr(face, "bbox") and face.bbox is not None else None,
                "kps": face.kps.tolist() if hasattr(face, "kps") and face.kps is not None else None,
                "det_score": float(face.det_score) if hasattr(face, "det_score") and face.det_score is not None else None,
                "embedding": norm_embedding,
                "embedding_raw": face.embedding
            })

        return results

    def extract_single_face_embedding(
        self,
        image_input: Union[np.ndarray, bytes, str, Path]
    ) -> List[float]:
        """
        Extract the 512-dimensional normalized face embedding from an image containing exactly one face.

        :param image_input: Image in any supported format
        :return: 512-dimensional float list representing the normalized face embedding
        :raises NoFaceDetectedError: When zero faces are detected
        :raises MultipleFacesDetectedError: When more than one face is detected
        """
        faces = self.detect_faces(image_input)

        if len(faces) == 0:
            raise NoFaceDetectedError("No face detected in the provided image.")

        if len(faces) > 1:
            raise MultipleFacesDetectedError(
                count=len(faces),
                message=f"Multiple faces detected ({len(faces)}). Please provide an image with exactly one face."
            )

        embedding = faces[0]["embedding"]
        if embedding is None or len(embedding) == 0:
            raise FaceRecognitionError("Face detected but embedding generation failed.")

        return embedding

    @staticmethod
    def compute_similarity(embedding1: Union[List[float], np.ndarray], embedding2: Union[List[float], np.ndarray]) -> float:
        """
        Compute cosine similarity between two face embeddings.
        Returns a float score typically in range [-1.0, 1.0], where >= 0.5 - 0.6 indicates a match.
        """
        vec1 = np.asarray(embedding1, dtype=np.float32)
        vec2 = np.asarray(embedding2, dtype=np.float32)

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))


# Global singleton instance for easy import across backend services
face_service = FaceRecognitionService()
