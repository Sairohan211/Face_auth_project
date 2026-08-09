"""
Isolated Gmail SMTP Diagnostic Test Script.

Verifies:
1. SMTP configuration presence (without exposing secrets)
2. Connection to smtp.gmail.com on port 587
3. STARTTLS negotiation
4. SMTP Authentication with Google App Password
5. Optional test email dispatch if GMAIL_TEST_RECIPIENT is provided

Security:
- Never prints or logs passwords, App Passwords, OTPs, or tokens.
"""

import os
import sys
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Ensure environment is loaded from backend/.env
backend_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=backend_env_path)

from app.core.config import settings

def run_diagnostic():
    print("==========================================================")
    print("Gmail SMTP Email Service Diagnostic")
    print("==========================================================\n")

    smtp_host = settings.GMAIL_SMTP_HOST or "smtp.gmail.com"
    smtp_port = settings.GMAIL_SMTP_PORT or 587
    smtp_user = settings.GMAIL_SMTP_USERNAME or ""
    smtp_pass = settings.GMAIL_SMTP_PASSWORD or ""
    from_email = settings.GMAIL_FROM_EMAIL or f"FaceAuthSystem <{smtp_user}>"

    user_configured = bool(smtp_user and len(smtp_user.strip()) > 0)
    pass_configured = bool(
        smtp_pass
        and smtp_pass not in ["YOUR_GOOGLE_APP_PASSWORD_HERE", "your_google_app_password_here"]
        and len(smtp_pass.strip()) > 0
    )

    print(f"SMTP host: {smtp_host}")
    print(f"SMTP port: {smtp_port}")
    print(f"Username configured: {str(user_configured).lower()}")
    print(f"Password configured: {str(pass_configured).lower()}")

    if not user_configured or not pass_configured:
        print("TLS: skipped (missing credentials)")
        print("Authentication: skipped (missing credentials)")
        print("Test email sent: false")
        print("\n[FAIL] Gmail SMTP username or App Password is not configured in backend/.env")
        print("==========================================================\n")
        return False

    server = None
    tls_success = False
    auth_success = False
    email_sent = False

    try:
        # 1. Connect
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
        server.ehlo()

        # 2. STARTTLS
        server.starttls()
        server.ehlo()
        tls_success = True
        print(f"TLS: successful")

        # 3. Authenticate
        server.login(smtp_user, smtp_pass)
        auth_success = True
        print(f"Authentication: successful")

        # 4. Optional test email dispatch
        test_recipient = settings.GMAIL_TEST_RECIPIENT or os.getenv("GMAIL_TEST_RECIPIENT", "")
        if test_recipient and test_recipient.strip():
            clean_recipient = test_recipient.strip().lower()
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "FaceAuthSystem - Gmail SMTP Diagnostic Test"
            msg["From"] = from_email
            msg["To"] = clean_recipient

            text_body = "FaceAuthSystem Diagnostic Test: Gmail SMTP delivery is functioning correctly."
            html_body = """<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #0b0914; color: #ffffff; padding: 20px;">
  <h2>FaceAuthSystem Diagnostic Test</h2>
  <p>This is an automated verification message to confirm Gmail SMTP delivery.</p>
</body>
</html>"""
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            server.sendmail(smtp_user, [clean_recipient], msg.as_string())
            email_sent = True
            print(f"Test email sent: true (to configured GMAIL_TEST_RECIPIENT)")
        else:
            print("Test email sent: false (GMAIL_TEST_RECIPIENT not set - skipping dispatch)")

        print("\n----------------------------------------------------------")
        print("DIAGNOSTIC SUMMARY")
        print("----------------------------------------------------------")
        print("[OK] Gmail SMTP connection and authentication verified successfully.")
        print("==========================================================\n")
        return True

    except smtplib.SMTPAuthenticationError as auth_err:
        print(f"TLS: {'successful' if tls_success else 'failed'}")
        print("Authentication: failed (Invalid Google App Password or Username)")
        print("Test email sent: false")
        print(f"\n[FAIL] Authentication failed: {auth_err}")
        print("==========================================================\n")
        return False
    except Exception as exc:
        print(f"TLS: {'successful' if tls_success else 'failed'}")
        print(f"Authentication: {'successful' if auth_success else 'failed'}")
        print("Test email sent: false")
        print(f"\n[FAIL] SMTP error: {exc}")
        print("==========================================================\n")
        return False
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass

if __name__ == "__main__":
    success = run_diagnostic()
    sys.exit(0 if success else 1)
