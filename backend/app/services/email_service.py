"""
Email service using Gmail SMTP (and fallback/legacy Resend) for FaceAuthSystem transactional notifications and OTP verification.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Dict, Any, Tuple, Optional
try:
    import resend
except ImportError:
    resend = None

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_verification_otp_email(
    recipient_email: str,
    recipient_name: str,
    otp: str
) -> Tuple[bool, Optional[str]]:
    """
    Sends the 6-digit registration/resend OTP verification email using Gmail SMTP.

    Security:
    - Never logs the raw OTP or OTP hash.
    - Never exposes or logs SMTP credentials.
    - Reads host, port, username, password from settings.
    - Uses STARTTLS.

    Returns:
        (success: bool, error_message: Optional[str])
    """
    clean_email = recipient_email.strip().lower()
    clean_name = recipient_name.strip() if recipient_name else "User"

    # Mask recipient email for safe logging
    masked_email = "***"
    if "@" in clean_email:
        parts = clean_email.split("@")
        name = parts[0]
        domain = parts[1]
        masked_name = name[:2] + "***" if len(name) > 2 else name + "***"
        masked_email = f"{masked_name}@{domain}"

    smtp_host = settings.GMAIL_SMTP_HOST or "smtp.gmail.com"
    smtp_port = settings.GMAIL_SMTP_PORT or 587
    smtp_user = settings.GMAIL_SMTP_USERNAME
    smtp_pass = settings.GMAIL_SMTP_PASSWORD
    from_email = settings.GMAIL_FROM_EMAIL or f"FaceAuthSystem <{smtp_user}>"

    if not smtp_user or not smtp_pass or smtp_pass in ["YOUR_GOOGLE_APP_PASSWORD_HERE", "your_google_app_password_here"]:
        err_msg = "Gmail SMTP credentials are not configured in backend/.env"
        logger.warning(f"[EMAIL SERVICE] Dispatch skipped for {masked_email}: {err_msg}")
        return False, err_msg

    subject = "Your FaceAuthSystem verification code"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0914; color: #f3f4f6; margin: 0; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #141224; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 36px 28px; text-align: center;">
    <div style="display: inline-block; padding: 6px 16px; background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 20px; font-size: 13px; font-weight: 600; color: #c4b5fd; margin-bottom: 20px;">
      FaceAuthSystem
    </div>
    
    <h2 style="color: #ffffff; font-size: 22px; font-weight: 700; margin: 0 0 12px 0;">Hello {clean_name},</h2>
    <p style="color: #9ca3af; font-size: 14px; margin: 0 0 24px 0;">Your email verification code is:</p>
    
    <div style="background: rgba(139, 92, 246, 0.12); border: 1.5px solid rgba(139, 92, 246, 0.45); border-radius: 12px; font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #ffffff; padding: 18px 24px; margin-bottom: 24px; display: inline-block; font-family: monospace;">
      {otp}
    </div>
    
    <p style="color: #a78bfa; font-size: 13px; font-weight: 500; margin: 0 0 20px 0;">This code expires in 5 minutes.</p>
    
    <hr style="border: none; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 24px 0;" />
    
    <p style="color: #6b7280; font-size: 12px; margin: 0; line-height: 1.5;">
      If you did not create this account, you can safely ignore this email.
    </p>

    <p style="color: #9ca3af; font-size: 13px; margin-top: 20px;">
      Regards,<br />FaceAuthSystem Team
    </p>
  </div>
</body>
</html>"""

    text_content = f"""FaceAuthSystem

Hello {clean_name},

Your email verification code is:

{otp}

This code expires in 5 minutes.

If you did not create this account, you can safely ignore this email.

Regards,
FaceAuthSystem Team
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = clean_email

    # Attach plain text then HTML
    part1 = MIMEText(text_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    server = None
    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [clean_email], msg.as_string())
        logger.info(f"[EMAIL SERVICE] Successfully sent verification OTP email via Gmail SMTP to {masked_email}")
        return True, None
    except smtplib.SMTPAuthenticationError as auth_err:
        err_msg = "Gmail SMTP authentication failed. Please verify Google App Password."
        logger.error(f"[EMAIL SERVICE] SMTP Auth error for {masked_email}: {err_msg}")
        return False, err_msg
    except Exception as exc:
        err_msg = str(exc)
        logger.error(f"[EMAIL SERVICE] SMTP dispatch error for {masked_email}: {err_msg}")
        return False, err_msg
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


# ==========================================
# Legacy / Fallback Resend Service (Kept for compatibility)
# ==========================================

def send_otp_email(to_email: str, otp_code: str) -> bool:
    """Legacy Resend OTP email function."""
    success, _, _ = send_email_with_diagnostics(
        to_email=to_email,
        subject="Your FaceAuthSystem verification code",
        otp_code=otp_code
    )
    return success

def send_email_with_diagnostics(
    to_email: str,
    subject: str,
    otp_code: Optional[str] = None,
    custom_html: Optional[str] = None,
    custom_text: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Legacy Resend email sender."""
    if not resend:
        return False, None, "Resend SDK is not installed."

    if not settings.RESEND_API_KEY or settings.RESEND_API_KEY == "your_resend_api_key_here":
        err_msg = "Resend API key is not configured in environment variables."
        return False, None, err_msg

    resend.api_key = settings.RESEND_API_KEY
    from_email = settings.RESEND_FROM_EMAIL or "FaceAuthSystem <onboarding@resend.dev>"

    html_content = custom_html or (f"<p>Your code is {otp_code}</p>" if otp_code else "<p>FaceAuthSystem Notification</p>")
    text_content = custom_text or (f"Your code is {otp_code}" if otp_code else "FaceAuthSystem Notification")

    try:
        params: resend.Emails.SendParams = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }
        res: Any = resend.Emails.send(params)
        msg_id = res.get("id") if isinstance(res, dict) else getattr(res, "id", None)
        return True, msg_id, None
    except Exception as exc:
        return False, None, str(exc)
