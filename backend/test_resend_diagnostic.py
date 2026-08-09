"""
Isolated Backend Diagnostic Script for Resend Email Integration (STEP 30).

Diagnoses:
1. Resend SDK installation & version
2. Backend environment loading (.env)
3. API key and Sender configuration presence (without exposing secrets)
4. Isolated test email dispatch
5. Capturing Resend API message ID or exact sanitized error message
6. Verification of sandbox restrictions (onboarding@resend.dev recipient rules)

Security:
- Never prints or logs the raw API key.
- Never prints OTPs, passwords, or tokens.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment is loaded from backend/.env
backend_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=backend_env_path)

from app.core.config import settings
from app.services import email_service

def run_diagnostic():
    print("==========================================================")
    print("Resend Email Service Diagnostic (STEP 30)")
    print("==========================================================\n")

    # 1. SDK Installation Check
    sdk_installed = False
    sdk_version = "None"
    try:
        import resend
        sdk_installed = True
        sdk_version = getattr(resend, "__version__", "unknown")
    except ImportError:
        sdk_installed = False

    # 2. Configuration Checks (without exposing secrets)
    api_key = settings.RESEND_API_KEY
    api_key_configured = bool(api_key and api_key != "your_resend_api_key_here" and len(api_key.strip()) > 0)
    
    from_email = settings.RESEND_FROM_EMAIL
    from_email_configured = bool(from_email and len(from_email.strip()) > 0)

    # Test recipient resolution
    test_recipient = os.getenv("RESEND_TEST_EMAIL")
    if not test_recipient or test_recipient == "your_test_email@example.com":
        # Safe default test address for Resend validation
        test_recipient = "delivered@resend.dev"
        recipient_source = "default Resend test recipient (delivered@resend.dev)"
    else:
        recipient_source = f"RESEND_TEST_EMAIL environment variable ({test_recipient})"

    print(f"Resend configured: {str(api_key_configured).lower()}")
    print(f"Sender configured: {str(from_email_configured).lower()}")
    print(f"SDK installed: {str(sdk_installed).lower()} (version: {sdk_version})")
    print(f"Test Recipient: {recipient_source}")

    if not api_key_configured:
        print("API request attempted: false")
        print("Resend request succeeded: false")
        print("Resend message ID: None")
        print("Error type/message: RESEND_API_KEY is not configured in backend/.env")
        return

    # 3. Attempt Isolated Diagnostic Dispatch
    api_request_attempted = True
    print(f"API request attempted: {str(api_request_attempted).lower()}")

    success, message_id, error_msg = email_service.send_email_with_diagnostics(
        to_email=test_recipient,
        subject="FaceAuthSystem - Diagnostic Test Verification",
        custom_html="""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #0b0914; color: #ffffff; padding: 20px;">
  <h2>FaceAuthSystem Diagnostic Test</h2>
  <p>This is an automated diagnostic verification message to confirm Resend delivery.</p>
</body>
</html>""",
        custom_text="FaceAuthSystem Diagnostic Test: This is an automated verification message."
    )

    print(f"Resend request succeeded: {str(success).lower()}")
    print(f"Resend message ID: {message_id if message_id else 'None'}")
    print(f"Error type/message: {error_msg if error_msg else 'None'}")

    print("\n----------------------------------------------------------")
    print("DETAILED DIAGNOSTIC FINDINGS")
    print("----------------------------------------------------------")
    if success:
        print(f"[OK] Resend successfully accepted the email with Message ID: {message_id}")
        print("[OK] Email dispatch is visible in the Resend dashboard at https://resend.com/emails")
    else:
        print(f"[FAIL] Resend dispatch failed with reason:")
        print(f"       {error_msg}")

    print("\n----------------------------------------------------------")
    print("SENDER DOMAIN & SANDBOX EVALUATION")
    print("----------------------------------------------------------")
    print(f"Current Sender: {from_email}")
    if "onboarding@resend.dev" in from_email:
        print("Sender Type: Resend Free Sandbox Domain (onboarding@resend.dev)")
        print("SANDBOX RULES:")
        print("1. In Resend development/sandbox mode (without a custom verified domain),")
        print("   Resend ONLY delivers emails to the account owner's registered email address.")
        print("2. Sending to arbitrary unverified email addresses (e.g. test@gmail.com, example.com)")
        print("   will be rejected by Resend with: 'You can only send testing emails to your own email address'.")
        print("3. To deliver OTPs to any user in production, verify a domain in Resend (resend.com/domains)")
        print("   and update RESEND_FROM_EMAIL=FaceAuthSystem <auth@yourdomain.com>.")
    print("==========================================================\n")

if __name__ == "__main__":
    run_diagnostic()
