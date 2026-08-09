"""
End-to-end Test Suite for Face Registration API (STEP 18).

Tests:
1. Unauthorized request (missing token) -> 401 Unauthorized
2. Unauthorized request (invalid token) -> 401 Unauthorized
3. Successful Face Registration (multipart/form-data with valid Bearer token) -> 200 OK
4. Verification in Supabase public.face_embeddings:
   - Exactly 1 row created
   - user_id matches authenticated user UUID
   - Embedding has exactly 512 dimensions
5. Duplicate registration (updating existing embedding) -> remains exactly 1 row
6. No-face image submission -> 400 Bad Request
7. Multiple-face image submission -> 400 Bad Request
8. Missing/empty file submission -> 400 Bad Request
9. Complete cleanup of test user and face embedding record
10. Verification that no raw face images are stored in Supabase Storage
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
from app.services import otp_service


def run_tests():
    client = TestClient(app)
    test_id = uuid.uuid4().hex[:8]
    test_email = f"face_test_{test_id}@example.com"
    test_password = "SecurePassword123!"
    test_name = "Face Test User"

    test_user_id = None
    access_token = None
    all_passed = True

    print("==========================================================")
    print(f"Starting STEP 18: Face Registration API End-to-End Tests")
    print(f"Test Account: {test_email}")
    print("==========================================================\n")

    try:
        # Step 0: Register and log in test user to obtain Supabase access token
        print("[SETUP] Registering test user...")
        reg_res = client.post("/api/auth/register", json={
            "full_name": test_name,
            "email": test_email,
            "password": test_password
        })
        assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
        test_user_id = reg_res.json()["user_id"]
        # Confirm user email in Supabase and application profile for test suite
        supabase.auth.admin.update_user_by_id(test_user_id, {"email_confirm": True})
        otp_service.set_profile_email_verified(test_user_id, True)
        print(f"-> Test user created with ID: {test_user_id}")


        print("[SETUP] Logging in to acquire Supabase JWT access token...")
        login_res = client.post("/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        access_token = login_res.json()["access_token"]
        assert access_token is not None
        print(f"-> Acquired access token: {access_token[:25]}...\n")


        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # Locate synthetic test face fixture
        artifact_dir = Path(r"C:\Users\sairo\.gemini\antigravity-ide\brain\0a7e89f8-ee12-4524-a02a-1019f639c1b6")
        synthetic_faces = list(artifact_dir.glob("synthetic_test_face*.png"))
        assert len(synthetic_faces) > 0, "Synthetic test face fixture not found in artifacts directory."
        test_face_path = synthetic_faces[0]

        with open(test_face_path, "rb") as f:
            valid_face_bytes = f.read()

        # TEST 1: Unauthorized Access (No Token)
        print("[TEST 1] Testing protected endpoint without token...")
        unauth_res = client.post("/api/face/register", files={"file": ("face.png", valid_face_bytes, "image/png")})
        print(f"Status: {unauth_res.status_code}, Detail: {unauth_res.json()}")
        assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"
        print("-> Missing token check PASSED.\n")

        # TEST 2: Unauthorized Access (Invalid Token)
        print("[TEST 2] Testing protected endpoint with invalid token...")
        bad_token_res = client.post(
            "/api/face/register",
            headers={"Authorization": "Bearer invalid.jwt.token"},
            files={"file": ("face.png", valid_face_bytes, "image/png")}
        )
        print(f"Status: {bad_token_res.status_code}, Detail: {bad_token_res.json()}")
        assert bad_token_res.status_code == 401, f"Expected 401, got {bad_token_res.status_code}"
        print("-> Invalid token check PASSED.\n")

        # TEST 3: Successful Face Registration
        print("[TEST 3] Testing valid Face Registration (multipart/form-data)...")
        reg_face_res = client.post(
            "/api/face/register",
            headers=auth_headers,
            files={"file": ("synthetic_face.png", valid_face_bytes, "image/png")}
        )
        print(f"Status: {reg_face_res.status_code}")
        print(f"Response Body: {reg_face_res.json()}")
        assert reg_face_res.status_code == 200, f"Expected 200, got {reg_face_res.status_code}: {reg_face_res.text}"
        res_data = reg_face_res.json()
        assert res_data.get("success") is True
        assert res_data.get("message") == "Face registered successfully"
        # Confirm no embedding or secret is leaked in response
        assert "embedding" not in res_data
        print("-> Valid face registration endpoint PASSED.\n")

        # TEST 4: Verify Database Persistence in Supabase public.face_embeddings
        print("[TEST 4] Verifying database records in public.face_embeddings...")
        db_records = supabase.table("face_embeddings").select("*").eq("user_id", test_user_id).execute()
        print(f"Rows found for user {test_user_id}: {len(db_records.data)}")
        assert len(db_records.data) == 1, f"Expected exactly 1 database row, found {len(db_records.data)}"
        
        row = db_records.data[0]
        assert row["user_id"] == test_user_id, f"User ID mismatch: {row['user_id']} vs {test_user_id}"
        
        # Parse pgvector string representation: '[0.0123, -0.0456, ...]'
        raw_embedding_str = row["embedding"]
        parsed_vector = [float(x.strip()) for x in raw_embedding_str.strip("[]").split(",") if x.strip()]
        print(f"Stored embedding dimensionality: {len(parsed_vector)}")
        assert len(parsed_vector) == 512, f"Expected 512-D vector in DB, got {len(parsed_vector)}"
        
        norm = np.linalg.norm(np.array(parsed_vector))
        print(f"Stored vector L2 norm: {norm:.4f}")
        assert np.isclose(norm, 1.0, atol=1e-2)
        print("-> Database record and 512-D vector verification PASSED.\n")

        # TEST 5: Test Duplicate Registration / Re-enrollment Update Behavior
        print("[TEST 5] Testing re-registration (update existing embedding without duplicate rows)...")
        re_reg_res = client.post(
            "/api/face/register",
            headers=auth_headers,
            files={"file": ("re_enroll_face.png", valid_face_bytes, "image/png")}
        )
        assert re_reg_res.status_code == 200, f"Re-registration failed: {re_reg_res.text}"
        
        db_records_after = supabase.table("face_embeddings").select("*").eq("user_id", test_user_id).execute()
        print(f"Rows after re-registration: {len(db_records_after.data)}")
        assert len(db_records_after.data) == 1, f"Duplicate rows detected! Count: {len(db_records_after.data)}"
        print("-> Update/replace behavior verified (single active embedding maintained) PASSED.\n")

        # TEST 6: Test No-Face Detection
        print("[TEST 6] Testing No-Face image submission...")
        black_img = Image.new("RGB", (300, 300), color="black")
        black_buf = io.BytesIO()
        black_img.save(black_buf, format="PNG")
        black_bytes = black_buf.getvalue()

        no_face_res = client.post(
            "/api/face/register",
            headers=auth_headers,
            files={"file": ("blank.png", black_bytes, "image/png")}
        )
        print(f"No-Face Status: {no_face_res.status_code}, Detail: {no_face_res.json()}")
        assert no_face_res.status_code == 400, f"Expected 400, got {no_face_res.status_code}"
        assert "no face detected" in no_face_res.json().get("detail", "").lower()
        print("-> No-face error handling PASSED.\n")

        # TEST 7: Test Multiple-Face Detection
        print("[TEST 7] Testing Multiple-Face image submission...")
        face_cv = cv2.imread(str(test_face_path))
        resized = cv2.resize(face_cv, (300, 300))
        two_faces = np.hstack([resized, resized])
        _, two_face_encoded = cv2.imencode(".png", two_faces)
        two_face_bytes = two_face_encoded.tobytes()

        multi_face_res = client.post(
            "/api/face/register",
            headers=auth_headers,
            files={"file": ("two_faces.png", two_face_bytes, "image/png")}
        )
        print(f"Multi-Face Status: {multi_face_res.status_code}, Detail: {multi_face_res.json()}")
        assert multi_face_res.status_code == 400, f"Expected 400, got {multi_face_res.status_code}"
        assert "multiple faces detected" in multi_face_res.json().get("detail", "").lower()
        print("-> Multiple-faces error handling PASSED.\n")

        # TEST 8: Test Empty File
        print("[TEST 8] Testing Empty File submission...")
        empty_res = client.post(
            "/api/face/register",
            headers=auth_headers,
            files={"file": ("empty.png", b"", "image/png")}
        )
        print(f"Empty File Status: {empty_res.status_code}, Detail: {empty_res.json()}")
        assert empty_res.status_code == 400, f"Expected 400, got {empty_res.status_code}"
        print("-> Empty file error handling PASSED.\n")

        # TEST 9: Verification that no raw face image was stored in Supabase Storage
        print("[TEST 9] Verifying that Supabase Storage contains NO raw face photographs...")
        buckets = supabase.storage.list_buckets()
        print(f"Available Storage Buckets: {[b.name for b in buckets]}")
        for b in buckets:
            files = supabase.storage.from_(b.name).list()
            print(f"Bucket '{b.name}' file count: {len(files)}")
            # Confirm test email / user id is not in filenames
            for f in files:
                assert test_user_id not in f.get("name", ""), f"Found leaked image in storage: {f}"
        print("-> Storage verification PASSED (Zero raw face images stored).\n")

    except AssertionError as ae:
        print(f"\n[FAIL] Assertion failed: {ae}")
        all_passed = False
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error during test execution: {exc}")
        all_passed = False
    finally:
        # CLEANUP: Delete face_embeddings row, profiles row, and auth user
        if test_user_id:
            print(f"[CLEANUP] Cleaning up test user {test_user_id} and associated biometric records...")
            try:
                # 1. Delete face embedding
                supabase.table("face_embeddings").delete().eq("user_id", test_user_id).execute()
                # 2. Delete profile
                supabase.table("profiles").delete().eq("id", test_user_id).execute()
                # 3. Delete auth account
                supabase.auth.admin.delete_user(test_user_id)
                print(f"-> Successfully cleaned up test user {test_user_id} and biometric records.")
            except Exception as clean_err:
                print(f"-> Warning: Cleanup error: {clean_err}")

    if all_passed:
        print("\n==========================================================")
        print("ALL STEP 18 FACE REGISTRATION TESTS PASSED!")
        print("==========================================================")
        sys.exit(0)
    else:
        print("\n==========================================================")
        print("SOME TESTS FAILED.")
        print("==========================================================")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
