"""
Comprehensive Test Suite for Face Verification API (STEP 21).

Test Scenarios:
1. Authenticated user + matching face -> verified = true, high match_score, similarity >= 0.40
2. Authenticated user + clearly different face -> verified = false, low match_score, similarity < 0.40
3. Unauthorized request (missing token) -> 401 Unauthorized
4. Unauthorized request (invalid token) -> 401 Unauthorized
5. Authenticated user with no registered face -> 404 Not Found
6. No-face image submission -> 400 Bad Request
7. Multiple-face image submission -> 400 Bad Request
8. User isolation / token verification: User A's token strictly retrieves User A's embedding, never User B's
9. Privacy & Storage check: Verification images and embeddings are never stored/persisted
10. Complete cleanup of all temporary test users and records from Supabase
"""

import io
import sys
import uuid
from pathlib import Path
import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.core.supabase import supabase
from app.core.config import settings
from app.services import otp_service


def run_tests():
    client = TestClient(app)
    
    # Generate unique test user credentials
    user_a_id_hex = uuid.uuid4().hex[:8]
    user_a_email = f"verify_test_a_{user_a_id_hex}@example.com"
    user_a_password = "SecurePassword123!"
    user_a_name = "Verify Test User A"

    user_b_id_hex = uuid.uuid4().hex[:8]
    user_b_email = f"verify_test_b_{user_b_id_hex}@example.com"
    user_b_password = "SecurePassword123!"
    user_b_name = "Verify Test User B"

    user_a_uuid = None
    user_b_uuid = None
    token_a = None
    token_b = None
    all_passed = True

    print("==========================================================")
    print("Starting STEP 21: Face Verification API End-to-End Tests")
    print(f"Configured Threshold: {settings.FACE_MATCH_THRESHOLD}")
    print(f"Test Account A: {user_a_email}")
    print(f"Test Account B: {user_b_email}")
    print("==========================================================\n")

    try:
        # ---------------------------------------------------------
        # SETUP: Create Users and Load Test Images
        # ---------------------------------------------------------
        print("[SETUP] Creating Test User A...")
        reg_a = client.post("/api/auth/register", json={
            "full_name": user_a_name,
            "email": user_a_email,
            "password": user_a_password
        })
        assert reg_a.status_code == 200, f"User A registration failed: {reg_a.text}"
        user_a_uuid = reg_a.json()["user_id"]
        # Confirm user email in Supabase and application profile for test suite
        supabase.auth.admin.update_user_by_id(user_a_uuid, {"email_confirm": True})
        otp_service.set_profile_email_verified(user_a_uuid, True)

        login_a = client.post("/api/auth/login", json={
            "email": user_a_email,
            "password": user_a_password
        })
        assert login_a.status_code == 200, f"User A login failed: {login_a.text}"
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        print(f"-> User A UUID: {user_a_uuid}, Token acquired.")

        print("[SETUP] Creating Test User B...")
        reg_b = client.post("/api/auth/register", json={
            "full_name": user_b_name,
            "email": user_b_email,
            "password": user_b_password
        })
        assert reg_b.status_code == 200, f"User B registration failed: {reg_b.text}"
        user_b_uuid = reg_b.json()["user_id"]
        # Confirm user email in Supabase and application profile for test suite
        supabase.auth.admin.update_user_by_id(user_b_uuid, {"email_confirm": True})
        otp_service.set_profile_email_verified(user_b_uuid, True)

        login_b = client.post("/api/auth/login", json={
            "email": user_b_email,
            "password": user_b_password
        })

        assert login_b.status_code == 200, f"User B login failed: {login_b.text}"
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        print(f"-> User B UUID: {user_b_uuid}, Token acquired.\n")


        # Load Face A image fixture
        face_a_matches = list(Path(r"C:\Users\sairo\.gemini\antigravity-ide\brain").glob("**/*synthetic_test_face*.png"))
        assert len(face_a_matches) > 0, "Synthetic face A fixture not found."
        face_a_path = face_a_matches[0]
        with open(face_a_path, "rb") as f:
            face_a_bytes = f.read()

        # Load Face B image fixture
        face_b_matches = list(Path(r"C:\Users\sairo\.gemini\antigravity-ide\brain").glob("**/*synthetic_face_person_b*.png"))
        assert len(face_b_matches) > 0, "Synthetic face B fixture not found."
        face_b_path = face_b_matches[0]
        with open(face_b_path, "rb") as f:
            face_b_bytes = f.read()

        # ---------------------------------------------------------
        # TEST 1: Unauthorized Request (Missing Token) -> 401
        # ---------------------------------------------------------
        print("[TEST 1] Testing protected /api/face/verify without token...")
        res_no_token = client.post("/api/face/verify", files={"file": ("face.png", face_a_bytes, "image/png")})
        print(f"Status: {res_no_token.status_code}, Response: {res_no_token.json()}")
        assert res_no_token.status_code == 401, f"Expected 401, got {res_no_token.status_code}"
        print("-> Missing token check PASSED.\n")

        # ---------------------------------------------------------
        # TEST 2: Unauthorized Request (Invalid Token) -> 401
        # ---------------------------------------------------------
        print("[TEST 2] Testing protected /api/face/verify with invalid token...")
        res_bad_token = client.post(
            "/api/face/verify",
            headers={"Authorization": "Bearer invalid.jwt.token"},
            files={"file": ("face.png", face_a_bytes, "image/png")}
        )
        print(f"Status: {res_bad_token.status_code}, Response: {res_bad_token.json()}")
        assert res_bad_token.status_code == 401, f"Expected 401, got {res_bad_token.status_code}"
        print("-> Invalid token check PASSED.\n")

        # ---------------------------------------------------------
        # TEST 3: User with No Registered Face -> 404
        # ---------------------------------------------------------
        print("[TEST 3] Testing verification for User A before face enrollment...")
        res_no_profile = client.post(
            "/api/face/verify",
            headers=headers_a,
            files={"file": ("face.png", face_a_bytes, "image/png")}
        )
        print(f"Status: {res_no_profile.status_code}, Detail: {res_no_profile.json()}")
        assert res_no_profile.status_code == 404, f"Expected 404, got {res_no_profile.status_code}"
        assert "no registered face" in res_no_profile.json().get("detail", "").lower()
        print("-> Missing registered face check PASSED.\n")

        # ---------------------------------------------------------
        # ENROLLMENT: Register Face A for User A, and Face B for User B
        # ---------------------------------------------------------
        print("[ENROLLMENT] Registering Face A for User A...")
        reg_face_a = client.post(
            "/api/face/register",
            headers=headers_a,
            files={"file": ("face_a.png", face_a_bytes, "image/png")}
        )
        assert reg_face_a.status_code == 200, f"Face A registration failed: {reg_face_a.text}"

        print("[ENROLLMENT] Registering Face B for User B...")
        reg_face_b = client.post(
            "/api/face/register",
            headers=headers_b,
            files={"file": ("face_b.png", face_b_bytes, "image/png")}
        )
        assert reg_face_b.status_code == 200, f"Face B registration failed: {reg_face_b.text}"
        print("-> Face enrollments complete.\n")

        # Count embeddings in DB before verification tests
        count_before_a = len(supabase.table("face_embeddings").select("id").eq("user_id", user_a_uuid).execute().data)
        assert count_before_a == 1

        # ---------------------------------------------------------
        # TEST 4: Matching Face Verification -> verified = True
        # ---------------------------------------------------------
        print("[TEST 4] Testing User A with Matching Face A...")
        res_match = client.post(
            "/api/face/verify",
            headers=headers_a,
            files={"file": ("verify_face_a.png", face_a_bytes, "image/png")}
        )
        print(f"Status: {res_match.status_code}")
        print(f"Response: {res_match.json()}")
        assert res_match.status_code == 200, f"Expected 200, got {res_match.status_code}: {res_match.text}"
        data_match = res_match.json()
        assert data_match["success"] is True
        assert data_match["verified"] is True
        assert data_match["similarity"] >= settings.FACE_MATCH_THRESHOLD
        assert data_match["match_score"] >= 90.0
        assert data_match["message"] == "Face verification successful"
        # Confirm no embeddings or sensitive data leaked in response
        assert "embedding" not in data_match
        print("-> Matching face verification PASSED.\n")

        # ---------------------------------------------------------
        # TEST 5: Non-Matching Face Verification -> verified = False
        # ---------------------------------------------------------
        print("[TEST 5] Testing User A with Non-Matching Face B...")
        res_diff = client.post(
            "/api/face/verify",
            headers=headers_a,
            files={"file": ("verify_face_b.png", face_b_bytes, "image/png")}
        )
        print(f"Status: {res_diff.status_code}")
        print(f"Response: {res_diff.json()}")
        assert res_diff.status_code == 200, f"Expected 200, got {res_diff.status_code}: {res_diff.text}"
        data_diff = res_diff.json()
        assert data_diff["success"] is True
        assert data_diff["verified"] is False
        assert data_diff["similarity"] < settings.FACE_MATCH_THRESHOLD
        assert data_diff["message"] == "Face verification failed"
        assert "embedding" not in data_diff
        print("-> Non-matching face verification PASSED.\n")

        # ---------------------------------------------------------
        # TEST 6: User Isolation / Multi-tenant Token Security
        # ---------------------------------------------------------
        print("[TEST 6] Testing User Isolation (User B token verifying with Face B vs Face A)...")
        # User B with Face B -> Must match
        res_b_match = client.post(
            "/api/face/verify",
            headers=headers_b,
            files={"file": ("face_b.png", face_b_bytes, "image/png")}
        )
        assert res_b_match.json()["verified"] is True, "User B should match Face B"
        print(f"-> User B + Face B: verified = {res_b_match.json()['verified']}, similarity = {res_b_match.json()['similarity']}")

        # User B with Face A -> Must fail
        res_b_diff = client.post(
            "/api/face/verify",
            headers=headers_b,
            files={"file": ("face_a.png", face_a_bytes, "image/png")}
        )
        assert res_b_diff.json()["verified"] is False, "User B should not match Face A"
        print(f"-> User B + Face A: verified = {res_b_diff.json()['verified']}, similarity = {res_b_diff.json()['similarity']}")
        print("-> User isolation and token security PASSED.\n")

        # ---------------------------------------------------------
        # TEST 7: No Face Detected in Image -> 400
        # ---------------------------------------------------------
        print("[TEST 7] Testing No-Face image submission...")
        black_img = Image.new("RGB", (300, 300), color="black")
        black_buf = io.BytesIO()
        black_img.save(black_buf, format="PNG")
        black_bytes = black_buf.getvalue()

        res_no_face = client.post(
            "/api/face/verify",
            headers=headers_a,
            files={"file": ("blank.png", black_bytes, "image/png")}
        )
        print(f"Status: {res_no_face.status_code}, Response: {res_no_face.json()}")
        assert res_no_face.status_code == 400
        assert "no face detected" in res_no_face.json().get("detail", "").lower()
        print("-> No-face error handling PASSED.\n")

        # ---------------------------------------------------------
        # TEST 8: Multiple Faces Detected in Image -> 400
        # ---------------------------------------------------------
        print("[TEST 8] Testing Multiple-Face image submission...")
        face_cv = cv2.imread(str(face_a_path))
        resized = cv2.resize(face_cv, (300, 300))
        two_faces = np.hstack([resized, resized])
        _, two_face_encoded = cv2.imencode(".png", two_faces)
        two_face_bytes = two_face_encoded.tobytes()

        res_multi_face = client.post(
            "/api/face/verify",
            headers=headers_a,
            files={"file": ("two_faces.png", two_face_bytes, "image/png")}
        )
        print(f"Status: {res_multi_face.status_code}, Response: {res_multi_face.json()}")
        assert res_multi_face.status_code == 400
        assert "multiple faces detected" in res_multi_face.json().get("detail", "").lower()
        print("-> Multiple-faces error handling PASSED.\n")

        # ---------------------------------------------------------
        # TEST 9: Empty Image File -> 400
        # ---------------------------------------------------------
        print("[TEST 9] Testing Empty File submission...")
        res_empty = client.post(
            "/api/face/verify",
            headers=headers_a,
            files={"file": ("empty.png", b"", "image/png")}
        )
        print(f"Status: {res_empty.status_code}, Response: {res_empty.json()}")
        assert res_empty.status_code == 400
        print("-> Empty file error handling PASSED.\n")

        # ---------------------------------------------------------
        # TEST 10: Verification Persistence Check (Zero storage leak)
        # ---------------------------------------------------------
        print("[TEST 10] Verifying no verification images or embeddings were persisted...")
        # Check database rows for User A and User B (should still be exactly 1 each from enrollment)
        count_after_a = len(supabase.table("face_embeddings").select("id").eq("user_id", user_a_uuid).execute().data)
        count_after_b = len(supabase.table("face_embeddings").select("id").eq("user_id", user_b_uuid).execute().data)
        assert count_after_a == 1, f"Expected 1 embedding for User A, found {count_after_a}"
        assert count_after_b == 1, f"Expected 1 embedding for User B, found {count_after_b}"

        # Check storage buckets for any leaked verification images
        buckets = supabase.storage.list_buckets()
        for b in buckets:
            files = supabase.storage.from_(b.name).list()
            for f in files:
                assert user_a_uuid not in f.get("name", "")
                assert user_b_uuid not in f.get("name", "")
        print("-> Privacy & zero-storage persistence check PASSED.\n")

    except AssertionError as ae:
        print(f"\n[FAIL] Assertion failed: {ae}")
        all_passed = False
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error during test execution: {exc}")
        all_passed = False
    finally:
        # ---------------------------------------------------------
        # CLEANUP: Remove all test users, profiles, and embeddings
        # ---------------------------------------------------------
        print("[CLEANUP] Cleaning up all test users and biometric records...")
        for uid in [user_a_uuid, user_b_uuid]:
            if uid:
                try:
                    supabase.table("face_embeddings").delete().eq("user_id", uid).execute()
                    supabase.table("profiles").delete().eq("id", uid).execute()
                    supabase.auth.admin.delete_user(uid)
                    print(f"-> Successfully cleaned up user {uid}")
                except Exception as clean_err:
                    print(f"-> Cleanup warning for {uid}: {clean_err}")

    if all_passed:
        print("\n==========================================================")
        print("ALL STEP 21 FACE VERIFICATION TESTS PASSED SUCCESSFULLY!")
        print("==========================================================")
        sys.exit(0)
    else:
        print("\n==========================================================")
        print("SOME TESTS FAILED.")
        print("==========================================================")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
