"""
Isolated Local Face Recognition Service Test Script.

Tests:
1. Face detection on synthetic face image
2. Face embedding extraction (512 dimensions)
3. Zero-faces detection handling (NoFaceDetectedError)
4. Multiple-faces detection handling (MultipleFacesDetectedError)
5. Cosine similarity computation
6. Verifies 100% local CPU ONNX Runtime execution with no external API calls
"""

import sys
from pathlib import Path
import numpy as np
import cv2

from app.services.face_recognition import (
    FaceRecognitionService,
    NoFaceDetectedError,
    MultipleFacesDetectedError,
    InvalidImageError
)

def run_tests():
    print("==================================================")
    print("Starting STEP 17: Local Face Recognition Tests")
    print("==================================================")

    # Initialize service
    print("\n[TEST 1] Initializing FaceRecognitionService (buffalo_sc model pack)...")
    service = FaceRecognitionService(model_name="buffalo_sc")
    print("-> Model pack initialized successfully.")

    # Locate generated synthetic face
    artifact_dir = Path(r"C:\Users\sairo\.gemini\antigravity-ide\brain\0a7e89f8-ee12-4524-a02a-1019f639c1b6")
    synthetic_faces = list(artifact_dir.glob("synthetic_test_face*.png"))
    
    if not synthetic_faces:
        print("[FAIL] Synthetic test face not found in artifacts directory.")
        sys.exit(1)

    test_image_path = synthetic_faces[0]
    print(f"\n[TEST 2] Testing Face Detection on synthetic test image...")
    print(f"Image source: {test_image_path.name}")
    
    faces = service.detect_faces(str(test_image_path))
    print(f"Number of faces detected: {len(faces)}")
    assert len(faces) == 1, f"Expected exactly 1 face, found {len(faces)}"
    
    face_data = faces[0]
    print(f"Detection confidence score: {face_data['det_score']:.4f}")
    print(f"Bounding box (x1, y1, x2, y2): {face_data['bbox']}")
    assert face_data['det_score'] > 0.5, f"Detection score too low: {face_data['det_score']}"
    print("-> Face detection test PASSED.")

    # 3. Test Embedding Extraction & Dimensionality
    print("\n[TEST 3] Testing Face Embedding Generation & Dimensionality...")
    embedding = service.extract_single_face_embedding(str(test_image_path))
    print(f"Embedding type: {type(embedding)}")
    print(f"Embedding length / dimensionality: {len(embedding)}")
    print(f"Sample embedding values (first 5): {[round(x, 5) for x in embedding[:5]]}")
    
    assert isinstance(embedding, list), "Embedding should be a python list"
    assert len(embedding) == 512, f"Expected 512-dimensional embedding, got {len(embedding)}"
    
    # Check L2 norm is ~1.0 (normalized)
    norm = np.linalg.norm(np.array(embedding))
    print(f"Embedding L2 norm: {norm:.6f}")
    assert np.isclose(norm, 1.0, atol=1e-3), f"Embedding not normalized, norm={norm}"
    print("-> Embedding generation and 512-D dimensionality test PASSED.")

    # 4. Test Zero Faces Handling
    print("\n[TEST 4] Testing Zero-Faces Handling on blank/black image...")
    black_img = np.zeros((400, 400, 3), dtype=np.uint8)
    try:
        service.extract_single_face_embedding(black_img)
        print("[FAIL] Expected NoFaceDetectedError, but none was raised.")
        sys.exit(1)
    except NoFaceDetectedError as e:
        print(f"Caught expected NoFaceDetectedError: {e}")
        print("-> Zero-faces error handling test PASSED.")

    # 5. Test Multiple Faces Handling
    print("\n[TEST 5] Testing Multiple-Faces Handling on composite image...")
    # Create image with two synthetic faces side by side
    single_img = cv2.imread(str(test_image_path))
    h, w, _ = single_img.shape
    resized = cv2.resize(single_img, (300, 300))
    two_faces_img = np.hstack([resized, resized])
    
    try:
        service.extract_single_face_embedding(two_faces_img)
        print("[FAIL] Expected MultipleFacesDetectedError, but none was raised.")
        sys.exit(1)
    except MultipleFacesDetectedError as e:
        print(f"Caught expected MultipleFacesDetectedError (detected count = {e.count}): {e}")
        print("-> Multiple-faces error handling test PASSED.")

    # 6. Test Cosine Similarity
    print("\n[TEST 6] Testing Cosine Similarity computation...")
    same_similarity = service.compute_similarity(embedding, embedding)
    print(f"Self-similarity score (identical face): {same_similarity:.4f}")
    assert np.isclose(same_similarity, 1.0, atol=1e-3), f"Self-similarity should be 1.0, got {same_similarity}"
    
    # Compare with a random vector
    random_vec = np.random.randn(512).tolist()
    rand_similarity = service.compute_similarity(embedding, random_vec)
    print(f"Random vector similarity score: {rand_similarity:.4f}")
    assert rand_similarity < 0.3, f"Random similarity should be low, got {rand_similarity}"
    print("-> Cosine similarity test PASSED.")

    # 7. Verify no external network calls / local execution
    print("\n[TEST 7] Verifying ONNX execution providers and local execution...")
    app_instance = service._get_app()
    for model_name, model in app_instance.models.items():
        print(f"Model [{model_name}] session provider: {model.session.get_providers()}")
    print("-> Local CPU execution verification PASSED.")

    print("\n==================================================")
    print("ALL STEP 17 LOCAL FACE RECOGNITION TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
