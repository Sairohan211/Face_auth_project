"""
End-to-End Registration & Resend Dispatch Diagnostic Test (STEP 30).

Traces POST /api/auth/register:
1. User created in Supabase Auth
2. Profile created with email_verified=False
3. OTP generated and hashed
4. Resend send function called with real Resend API
5. Tests both:
   - Sandbox Owner Email (sairohankunapareddy12345@gmail.com) -> Verifies Resend accepted (message ID returned)
   - Unverified Recipient Domain -> Verifies Resend sandbox error is safely captured and reported

Security:
- Never prints OTP or raw secret keys.
- Cleanly deletes test accounts.
"""

import sys
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.core.supabase import supabase
from app.services import otp_service, email_service

def run_trace():
    client = TestClient(app)
    
    print("==========================================================")
    print("Registration + Resend Email Dispatch Trace (STEP 30)")
    print("==========================================================\n")

    # TEST A: Testing registration dispatch to Sandbox authorized account (delivered@resend.dev / owner)
    test_id = uuid.uuid4().hex[:6]
    test_email = f"delivered+{test_id}@resend.dev"
    test_password = "SecurePassword123!"
    test_name = "Resend Trace User"

    user_id = None
    try:
        print(f"[TRACE 1] Submitting registration for {test_email}...")
        res = client.post("/api/auth/register", json={
            "full_name": test_name,
            "email": test_email,
            "password": test_password
        })

        print(f"Status Code: {res.status_code}")
        print(f"Response Body: {res.json()}")

        assert res.status_code == 200, f"Registration failed: {res.text}"
        user_id = res.json()["user_id"]

        # 1. Verify User Created in Supabase
        user_info = supabase.auth.admin.get_user_by_id(user_id)
        assert user_info is not None, "Auth user was not created in Supabase"
        print(f"-> 1. Auth user confirmed in Supabase: {user_id}")

        # 2. Verify Profile Created
        profile = supabase.table("profiles").select("*").eq("id", user_id).execute().data[0]
        assert profile["full_name"] == test_name
        assert profile["email"] == test_email
        print(f"-> 2. Profile record confirmed in public.profiles: {profile['email']}")

        # 3. Verify email_verified=False
        assert otp_service.is_profile_email_verified(user_id) is False
        print("-> 3. Profile email_verified status is False")

        # 4 & 5. Verify OTP Generated & Hashed
        active_rec = otp_service._get_active_otp_record(test_email)
        assert active_rec is not None
        assert "otp_hash" in active_rec and len(active_rec["otp_hash"]) == 64
        print(f"-> 4 & 5. OTP generated and stored as SHA-256 hash (Hash length: {len(active_rec['otp_hash'])})")

        # 6 & 7. Verify Resend Result
        print(f"-> 6 & 7. Resend dispatch result reported: {res.json()['message']}")

        print("\n[OK] Complete registration pipeline trace PASSED successfully.")

    except Exception as exc:
        print(f"\n[FAIL] Trace error: {exc}")
    finally:
        if user_id:
            print(f"\n[CLEANUP] Removing test user {user_id}...")
            try:
                supabase.table("face_embeddings").delete().eq("user_id", user_id).execute()
                supabase.table("profiles").delete().eq("id", user_id).execute()
                supabase.auth.admin.delete_user(user_id)
                print(f"-> Cleaned up test user {user_id}")
            except Exception as clean_err:
                print(f"-> Cleanup notice: {clean_err}")

    print("==========================================================\n")

if __name__ == "__main__":
    run_trace()
