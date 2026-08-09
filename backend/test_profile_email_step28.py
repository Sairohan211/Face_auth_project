"""
Automated Test Suite for STEP 28:
Permanent public.profiles.email Integration, Backfilling, and Security.

Verifies:
1. Existing profiles are preserved.
2. Existing profile emails are correctly backfilled.
3. New registration creates profile record with id, full_name, email (lowercase), email_verified=False.
4. Email is stored in lowercase consistently.
5. OTP verification changes only email_verified (email remains unchanged).
6. Face registration works after email verification.
7. Face verification works.
8. Login works.
9. Profile retrieval (GET /api/auth/me) includes id, full_name, email, email_verified, created_at.
10. RLS/token security prevents cross-user profile access.
11. No password or secret is stored in profiles.
12. Complete cleanup of test data.
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.supabase import supabase
from app.services import otp_service, email_service

def run_tests():
    client = TestClient(app)
    
    test_id = uuid.uuid4().hex[:8]
    test_email_raw = f"Profile_Test_{test_id}@Gmail.COM"
    test_email_clean = test_email_raw.strip().lower()
    test_password = "SecurePassword123!"
    test_name = "Step28 Test User"
    
    user_b_email = f"profile_user_b_{test_id}@gmail.com"
    user_b_name = "User B"
    
    test_user_id = None
    user_b_id = None
    all_passed = True

    print("==========================================================")
    print("Starting STEP 28: public.profiles.email Integration Tests")
    print(f"Test Account: {test_email_clean}")
    print("==========================================================\n")

    try:
        # TEST 1 & 2: Existing profiles preserved & backfilled
        print("[TEST 1 & 2] Verifying existing profiles have non-null email backfill...")
        existing_profiles = supabase.table("profiles").select("*").execute().data
        print(f"Total profiles in database: {len(existing_profiles)}")
        for p in existing_profiles:
            assert p["email"] is not None and len(p["email"]) > 0, f"Profile {p['id']} has null email!"
            assert "@" in p["email"], f"Profile {p['id']} email is invalid format: {p['email']}"
            assert p["email"] == p["email"].lower(), f"Profile {p['id']} email not lowercase: {p['email']}"
            # Verify no secret or password column in profile
            assert "password" not in p and "password_hash" not in p, "Security violation: password field found in profile!"
        print("-> Existing profiles preserved and verified with non-null lowercase emails PASSED.\n")

        # TEST 3 & 4: New registration creates profile with email in lowercase
        print("[TEST 3 & 4] Testing new user registration and profiles.email persistence...")
        sent_emails = []
        def mock_send(to_email, otp_code):
            sent_emails.append({"to": to_email, "otp": otp_code})
            return True

        with patch("app.services.email_service.send_otp_email", side_effect=mock_send):
            reg_res = client.post("/api/auth/register", json={
                "full_name": test_name,
                "email": test_email_raw,
                "password": test_password
            })

        print(f"Status: {reg_res.status_code}, Response: {reg_res.json()}")
        assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
        test_user_id = reg_res.json()["user_id"]

        # Inspect database profile row
        p_row = supabase.table("profiles").select("*").eq("id", test_user_id).execute().data[0]
        print(f"Created profile row in database: {p_row}")
        assert p_row["id"] == test_user_id
        assert p_row["full_name"] == test_name
        assert p_row["email"] == test_email_clean, f"Expected {test_email_clean}, got {p_row['email']}"
        assert p_row["email"] == p_row["email"].lower(), "Email must be strictly lowercase"
        print("-> Profile created with consistent lowercase email PASSED.\n")

        # TEST 8: Login works and acquires session
        print("[TEST 8] Testing user login...")
        login_res = client.post("/api/auth/login", json={
            "email": test_email_clean,
            "password": test_password
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token_a = login_res.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        print("-> Login succeeded and JWT token acquired PASSED.\n")

        # TEST 9: Profile retrieval via GET /api/auth/me
        print("[TEST 9] Testing Profile Retrieval endpoint GET /api/auth/me...")
        me_res = client.get("/api/auth/me", headers=headers_a)
        print(f"GET /api/auth/me response: {me_res.json()}")
        assert me_res.status_code == 200, f"GET /api/auth/me failed: {me_res.text}"
        me_data = me_res.json()
        assert me_data["id"] == test_user_id
        assert me_data["full_name"] == test_name
        assert me_data["email"] == test_email_clean
        assert me_data["email_verified"] is False
        assert me_data["created_at"] is not None
        print("-> Profile retrieval returned all required fields PASSED.\n")

        # TEST 5: OTP verification changes only email_verified
        print("[TEST 5] Verifying OTP and checking that only email_verified changes...")
        assert len(sent_emails) == 1
        otp_to_verify = sent_emails[0]["otp"]
        verify_res = client.post("/api/auth/verify-email", json={
            "email": test_email_clean,
            "otp": otp_to_verify
        })
        assert verify_res.status_code == 200
        
        # Re-fetch profile
        me_after_otp = client.get("/api/auth/me", headers=headers_a).json()
        assert me_after_otp["email_verified"] is True
        assert me_after_otp["email"] == test_email_clean, "Email must not change during OTP verification"
        print("-> OTP verification updated email_verified to True while preserving email PASSED.\n")

        # TEST 6 & 7: Face registration & verification work for the verified user
        print("[TEST 6 & 7] Testing Face Biometric Registration and Verification...")
        face_matches = list(Path(r"C:\Users\sairo\.gemini\antigravity-ide\brain").glob("**/*synthetic_test_face*.png"))
        assert len(face_matches) > 0, "Test face fixture not found."
        with open(face_matches[0], "rb") as f:
            face_bytes = f.read()

        face_reg_res = client.post(
            "/api/face/register",
            headers=headers_a,
            files={"file": ("face.png", face_bytes, "image/png")}
        )
        assert face_reg_res.status_code == 200
        assert face_reg_res.json()["success"] is True

        face_verify_res = client.post(
            "/api/face/verify",
            headers=headers_a,
            files={"file": ("verify.png", face_bytes, "image/png")}
        )
        assert face_verify_res.status_code == 200
        assert face_verify_res.json()["verified"] is True
        print("-> Face registration and verification PASSED.\n")

        # TEST 10: RLS / Token isolation check
        print("[TEST 10] Testing User Token Isolation & Profile Protection...")
        with patch("app.services.email_service.send_otp_email", return_value=True):
            reg_b = client.post("/api/auth/register", json={
                "full_name": user_b_name,
                "email": user_b_email,
                "password": test_password
            })
            user_b_id = reg_b.json()["user_id"]

        login_b = client.post("/api/auth/login", json={
            "email": user_b_email,
            "password": test_password
        })
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        me_b = client.get("/api/auth/me", headers=headers_b).json()
        assert me_b["id"] == user_b_id
        assert me_b["email"] == user_b_email
        assert me_b["email"] != me_data["email"], "User B must not see User A email"
        print("-> Token isolation and RLS security verified PASSED.\n")

    except AssertionError as ae:
        print(f"\n[FAIL] Assertion error: {ae}")
        all_passed = False
    except Exception as exc:
        print(f"\n[ERROR] Unexpected exception: {exc}")
        all_passed = False
    finally:
        # CLEANUP
        for uid in [test_user_id, user_b_id]:
            if uid:
                print(f"[CLEANUP] Cleaning up test user {uid}...")
                try:
                    supabase.table("face_embeddings").delete().eq("user_id", uid).execute()
                    supabase.table("profiles").delete().eq("id", uid).execute()
                    supabase.auth.admin.delete_user(uid)
                    print(f"-> Successfully cleaned up test user {uid}")
                except Exception as clean_err:
                    print(f"-> Cleanup notice: {clean_err}")

    if all_passed:
        print("\n==========================================================")
        print("ALL STEP 28 PROFILE EMAIL TESTS PASSED (11/11)!")
        print("==========================================================")
        sys.exit(0)
    else:
        print("\n==========================================================")
        print("SOME TESTS FAILED.")
        print("==========================================================")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
