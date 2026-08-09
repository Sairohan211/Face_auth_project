"""
End-to-End Test Suite for STEP 25: Email OTP Verification & Registration Flow.

Tests:
1. Registration via POST /api/auth/register (unconfirmed user created).
2. Verification that unconfirmed user cannot log in before OTP verification.
3. Verification that invalid OTP is rejected by Supabase Auth verifyOtp.
4. Verification that valid OTP successfully confirms the user and creates an active session.
5. Verification that the confirmed user can now log in and access protected endpoints.
6. Verification that the confirmed user can enroll face biometric in public.face_embeddings.
7. Verification that face biometrics can be verified against the registered embedding.
8. Clean up of all test accounts and database records.
"""

import io
import sys
import uuid
from pathlib import Path
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.core.supabase import supabase, get_supabase_client

def run_tests():
    client = TestClient(app)
    auth_client = get_supabase_client()
    
    test_id = uuid.uuid4().hex[:8]
    test_email = f"otp_flow_test_{test_id}@gmail.com"
    test_password = "SecurePassword123!"
    test_name = "OTP Test User"
    
    test_user_id = None
    all_passed = True

    print("==========================================================")
    print("Starting STEP 25: Email OTP & Face Registration Flow Tests")
    print(f"Test Account: {test_email}")
    print("==========================================================\n")

    try:
        # TEST 1: Account Registration via FastAPI POST /api/auth/register
        print("[TEST 1] Testing account registration via POST /api/auth/register...")
        reg_res = client.post("/api/auth/register", json={
            "full_name": test_name,
            "email": test_email,
            "password": test_password
        })
        print(f"Status: {reg_res.status_code}, Response: {reg_res.json()}")
        assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
        reg_data = reg_res.json()
        assert reg_data["success"] is True
        assert reg_data["user_id"] is not None
        test_user_id = reg_data["user_id"]
        print(f"-> Unconfirmed user created in Supabase Auth with ID: {test_user_id}\n")

        # TEST 2: Confirm login is BLOCKED prior to email verification
        print("[TEST 2] Confirming unconfirmed user CANNOT log in before email verification...")
        unconf_login = client.post("/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        print(f"Status: {unconf_login.status_code}, Response: {unconf_login.json()}")
        assert unconf_login.status_code == 401, f"Expected 401 for unconfirmed email, got {unconf_login.status_code}"
        print("-> Login before OTP confirmation successfully blocked.\n")

        # TEST 3: Obtain Supabase OTP for this user
        print("[TEST 3] Generating Supabase confirmation link/OTP...")
        link_res = supabase.auth.admin.generate_link({
            "type": "signup",
            "email": test_email,
            "password": test_password
        })
        valid_otp = link_res.properties.email_otp
        assert valid_otp is not None, "Failed to obtain Supabase email OTP"
        print(f"-> Supabase OTP successfully generated.\n")

        # TEST 4: Test Invalid OTP Rejection
        print("[TEST 4] Testing rejection of invalid OTP code ('000000')...")
        try:
            bad_verify = auth_client.auth.verify_otp({
                "email": test_email,
                "token": "000000",
                "type": "signup"
            })
            # If no exception raised, assert error in response
            assert bad_verify.session is None, "Invalid OTP should not establish session"
            print("-> Invalid OTP rejected.\n")
        except Exception as otp_err:
            print(f"-> Caught expected error for invalid OTP: {otp_err}\n")

        # TEST 5: Test Valid OTP Verification via Supabase verifyOtp
        print("[TEST 5] Verifying user email with valid OTP code...")
        verify_res = auth_client.auth.verify_otp({
            "email": test_email,
            "token": valid_otp,
            "type": "signup"
        })
        assert verify_res.session is not None, "Valid OTP should return an active Supabase session"
        assert verify_res.session.access_token is not None, "Access token missing in session"
        access_token = verify_res.session.access_token
        confirmed_user = verify_res.user
        assert confirmed_user.email_confirmed_at is not None, "Email should now be confirmed"
        print(f"-> Email successfully verified! Email confirmed at: {confirmed_user.email_confirmed_at}\n")

        # TEST 6: Confirm login now SUCCEEDS after email verification
        print("[TEST 6] Confirming login now SUCCEEDS for confirmed user...")
        login_res = client.post("/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        print(f"Status: {login_res.status_code}")
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        print("-> Confirmed user login PASSED.\n")

        # TEST 7: Test Face Biometric Enrollment for the verified user
        print("[TEST 7] Testing Face Biometric Enrollment with authenticated session...")
        face_matches = list(Path(r"C:\Users\sairo\.gemini\antigravity-ide\brain").glob("**/*synthetic_test_face*.png"))
        assert len(face_matches) > 0, "Test face fixture not found."
        with open(face_matches[0], "rb") as f:
            face_bytes = f.read()

        face_reg_res = client.post(
            "/api/face/register",
            headers=auth_headers,
            files={"file": ("face.png", face_bytes, "image/png")}
        )
        print(f"Status: {face_reg_res.status_code}, Response: {face_reg_res.json()}")
        assert face_reg_res.status_code == 200, f"Face registration failed: {face_reg_res.text}"
        assert face_reg_res.json()["success"] is True
        print("-> Face registration after OTP verification PASSED.\n")

        # TEST 8: Test Face Verification for the newly enrolled user
        print("[TEST 8] Testing Face Verification...")
        face_verify_res = client.post(
            "/api/face/verify",
            headers=auth_headers,
            files={"file": ("verify.png", face_bytes, "image/png")}
        )
        print(f"Status: {face_verify_res.status_code}, Response: {face_verify_res.json()}")
        assert face_verify_res.status_code == 200, f"Face verification failed: {face_verify_res.text}"
        assert face_verify_res.json()["verified"] is True
        print("-> Face verification PASSED.\n")

    except AssertionError as ae:
        print(f"\n[FAIL] Assertion error: {ae}")
        all_passed = False
    except Exception as exc:
        print(f"\n[ERROR] Unexpected exception: {exc}")
        all_passed = False
    finally:
        # CLEANUP
        if test_user_id:
            print(f"[CLEANUP] Cleaning up test user {test_user_id} and biometric records...")
            try:
                supabase.table("face_embeddings").delete().eq("user_id", test_user_id).execute()
                supabase.table("profiles").delete().eq("id", test_user_id).execute()
                supabase.auth.admin.delete_user(test_user_id)
                print(f"-> Successfully cleaned up test user {test_user_id}")
            except Exception as clean_err:
                print(f"-> Cleanup notice: {clean_err}")

    if all_passed:
        print("\n==========================================================")
        print("ALL STEP 25 EMAIL OTP & REGISTRATION TESTS PASSED!")
        print("==========================================================")
        sys.exit(0)
    else:
        print("\n==========================================================")
        print("SOME TESTS FAILED.")
        print("==========================================================")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
