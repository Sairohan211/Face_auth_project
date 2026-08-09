import os
from dotenv import load_dotenv

# Load .env file from root backend/ directory
load_dotenv()

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    # Use the service role key for administrative server operations
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
    # Biometric cosine similarity threshold (development starting point, not universal security threshold)
    FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.40"))
    # Resend API Key for transactional and security notification emails
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "FaceAuthSystem <onboarding@resend.dev>")
    RESEND_TEST_EMAIL: str = os.getenv("RESEND_TEST_EMAIL", "")

    # Gmail SMTP Configuration
    GMAIL_SMTP_HOST: str = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com")
    GMAIL_SMTP_PORT: int = int(os.getenv("GMAIL_SMTP_PORT", "587"))
    GMAIL_SMTP_USERNAME: str = os.getenv("GMAIL_SMTP_USERNAME", "naira.ai.face.auth@gmail.com")
    GMAIL_SMTP_PASSWORD: str = os.getenv("GMAIL_SMTP_PASSWORD", "")
    GMAIL_FROM_EMAIL: str = os.getenv("GMAIL_FROM_EMAIL", "FaceAuthSystem <naira.ai.face.auth@gmail.com>")
    GMAIL_TEST_RECIPIENT: str = os.getenv("GMAIL_TEST_RECIPIENT", "")


    def validate(self):
        if not self.SUPABASE_URL or not self.SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError(
                "Missing Supabase configuration. Please check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env."
            )

settings = Settings()
settings.validate()
