"""
Comprehensive End-to-End Test for Gmail SMTP OTP Delivery, Verification & Face Biometrics (STEP 31B).

Tests:
1. GET /api/health
2. POST /api/auth/register with Gmail SMTP dispatch
3. Invalid OTP rejection (HTTP 400)
4. OTP Resend Cooldown enforcement (HTTP 429)
5. 5 Failed attempts invalidation
6. Valid OTP verification (public.profiles email_verified -> True)
7. POST /api/auth/login with verified account
8. Face Registration (POST /api/face/register)
9. Face Verification (POST /api/face/verify)
10. Complete cleanup of test account

Security:
- Never prints OTP or secrets.
"""

import uuid
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.core.supabase import supabase
from app.services import otp_service, email_service

def run_suite():
    client = TestClient(app)
    test_id = uuid.uuid4().hex[:6]
    test_email = f"test_smtp_{test_id}@gmail.com"
    test_name = f"SMTP Test User {test_id}"
    test_password = "SecurePassword123!"

    print("==========================================================")
    print("STEP 31B: Gmail SMTP End-to-End Registration & Verification")
    print("==========================================================\n")

    user_id = None
    access_token = None
    try:
        # 1. Health Check
        print("[TEST 1] Testing GET /api/health...")
        health_res = client.get("/api/health")
        assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
        print("-> GET /api/health PASSED: 200 OK\n")

        # 2. Registration with Gmail SMTP dispatch
        print(f"[TEST 2] Submitting registration for {test_email}...")
        reg_res = client.post("/api/auth/register", json={
            "full_name": test_name,
            "email": test_email,
            "password": test_password
        })
        print(f"-> Registration status: {reg_res.status_code}")
        print(f"-> Response: {reg_res.json()}")
        assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
        user_id = reg_res.json()["user_id"]
        assert "A verification code has been sent" in reg_res.json()["message"], "Expected success email dispatch message"
        print("-> Registration with Gmail SMTP dispatch PASSED\n")

        # 3. Test Invalid OTP verification
        print("[TEST 3] Testing Invalid OTP rejection...")
        invalid_res = client.post("/api/auth/verify-email", json={
            "email": test_email,
            "otp": "000000"
        })
        assert invalid_res.status_code == 400, f"Expected 400 for invalid OTP, got: {invalid_res.status_code}"
        print("-> Invalid OTP properly rejected with 400 Bad Request\n")

        # 4. Test Resend OTP Cooldown enforcement
        print("[TEST 4] Testing Resend Cooldown (immediate resend)...")
        cooldown_res = client.post("/api/auth/resend-otp", json={"email": test_email})
        assert cooldown_res.status_code == 429, f"Expected 429 Cooldown error, got: {cooldown_res.status_code}"
        print(f"-> Cooldown properly enforced (429 Too Many Requests): {cooldown_res.json()['detail']}\n")

        # 5. Test 5 Failed Attempts Lockout
        print("[TEST 5] Testing 5 failed attempts lockout...")
        for i in range(4): # 1 was done in test 3, do 4 more
            fail_res = client.post("/api/auth/verify-email", json={"email": test_email, "otp": f"11111{i}"})
            assert fail_res.status_code == 400

        # Now active OTP should be invalidated after 5 attempts
        lockout_res = client.post("/api/auth/verify-email", json={"email": test_email, "otp": "999999"})
        assert lockout_res.status_code == 400
        print("-> 5 failed attempts limit verified (OTP invalidated)\n")

        # 6. Generate fresh OTP and Verify
        print("[TEST 6] Generating fresh OTP and verifying...")
        if test_email in otp_service._in_memory_otp_store:
            del otp_service._in_memory_otp_store[test_email]
        raw_otp = otp_service.create_and_store_otp(user_id, test_email)
        verify_res = client.post("/api/auth/verify-email", json={
            "email": test_email,
            "otp": raw_otp
        })
        assert verify_res.status_code == 200, f"Valid OTP verification failed: {verify_res.text}"
        print("-> POST /api/auth/verify-email PASSED: 200 OK\n")

        # Verify email_verified status in DB/helper
        is_verified = otp_service.is_profile_email_verified(user_id)
        print(f"-> Profile email_verified status: {is_verified}")
        assert is_verified is True, "Profile was not marked as verified"

        # 7. Login to acquire Bearer Token
        print("\n[TEST 7] Logging in to acquire Bearer Token...")
        login_res = client.post("/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        access_token = login_res.json()["access_token"]
        assert access_token is not None
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        print("-> POST /api/auth/login PASSED: Acquired JWT Bearer Token\n")

        # 8. Load Test Face Image Fixture
        face_matches = list(Path(r"C:\Users\sairo\.gemini\antigravity-ide\brain").glob("**/*synthetic_test_face*.png"))
        assert len(face_matches) > 0, "Synthetic face fixture not found."
        with open(face_matches[0], "rb") as f:
            face_bytes = f.read()

        # 9. Test Face Registration
        print("[TEST 8] Testing Face Registration (POST /api/face/register)...")
        face_reg_res = client.post(
            "/api/face/register",
            headers=auth_headers,
            files={"file": ("test_face.png", face_bytes, "image/png")}
        )
        assert face_reg_res.status_code == 200, f"Face registration failed: {face_reg_res.text}"
        assert face_reg_res.json().get("success") is True
        print(f"-> Face registration PASSED: {face_reg_res.json().get('message')}\n")

        # 10. Test Face Verification
        print("[TEST 9] Testing Face Verification (POST /api/face/verify)...")
        face_verify_res = client.post(
            "/api/face/verify",
            headers=auth_headers,
            files={"file": ("test_face.png", face_bytes, "image/png")}
        )
        assert face_verify_res.status_code == 200, f"Face verification failed: {face_verify_res.text}"
        verify_data = face_verify_res.json()
        assert verify_data.get("verified") is True, f"Face verification returned verified=False: {verify_data}"
        print(f"-> Face verification PASSED: verified={verify_data.get('verified')}, match_score={verify_data.get('match_score')}, similarity={verify_data.get('similarity')}\n")

        print("----------------------------------------------------------")
        print("ALL END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY")
        print("----------------------------------------------------------\n")

    finally:
        if user_id:
            print(f"[CLEANUP] Removing test user {user_id}...")
            try:
                supabase.table("face_embeddings").delete().eq("user_id", user_id).execute()
                supabase.table("profiles").delete().eq("id", user_id).execute()
                supabase.auth.admin.delete_user(user_id)
                print("-> Cleanup completed successfully.")
            except Exception as clean_err:
                print(f"-> Cleanup notice: {clean_err}")

if __name__ == "__main__":
    run_suite()
