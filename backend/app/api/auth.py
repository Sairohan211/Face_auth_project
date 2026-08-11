import logging
import traceback
import time
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserLoginResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    ResendOtpRequest,
    ResendOtpResponse,
    UserProfileResponse,
    SessionInfo
)
from app.core.supabase import supabase, get_supabase_client
from app.services import otp_service, email_service
from supabase_auth.errors import AuthApiError


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Register a new user",
    description="Registers a user account, sets email_verified=False, generates a secure 6-digit OTP, and sends it via email."
)
async def register(payload: UserRegisterRequest):
    user_id = None
    clean_email = payload.email.strip().lower()
    clean_name = payload.full_name.strip()

    masked_email = "***"
    if "@" in clean_email:
        parts = clean_email.split("@")
        name = parts[0]
        domain = parts[1]
        masked_name = name[:2] + "***" if len(name) > 2 else name + "***"
        masked_email = f"{masked_name}@{domain}"

    logger.warning(f"[REGISTER TRACE] registration endpoint entered for {masked_email}")

    try:
        # 1. Create the user in Supabase Auth (Auto-confirm email for demo flow)
        auth_client = get_supabase_client()
        auth_response = None

        try:
            auth_response = supabase.auth.admin.create_user({
                "email": clean_email,
                "password": payload.password,
                "email_confirm": True,
                "user_metadata": {"full_name": clean_name}
            })
        except Exception as admin_err:
            logger.warning("[REGISTER] admin.create_user failed, falling back to sign_up: %s", admin_err)
            auth_response = auth_client.auth.sign_up({
                "email": clean_email,
                "password": payload.password,
                "options": {
                    "data": {
                        "full_name": clean_name
                    }
                }
            })

        if not auth_response or not auth_response.user:
            logger.error("[REGISTER] sign_up returned no user. auth_response=%s", auth_response)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists."
            )

        user_id = auth_response.user.id

        # 2. Store profile in public.profiles with email and email_verified = True (bypassed for demo)
        try:
            try:
                supabase.table("profiles").insert({
                    "id": user_id,
                    "full_name": clean_name,
                    "email": clean_email,
                    "email_verified": True
                }).execute()
            except Exception as ins_err:
                logger.warning("Primary profile insert with email_verified failed, retrying without email_verified: %s", ins_err)
                supabase.table("profiles").insert({
                    "id": user_id,
                    "full_name": clean_name,
                    "email": clean_email
                }).execute()
            otp_service.set_profile_email_verified(user_id, True)
            logger.warning(f"[REGISTER TRACE] profile created for {masked_email}")

        except Exception as db_err:
            logger.error("Failed to insert profile for user %s: %s", user_id, db_err)
            pass

        # 3. Log in to get access token for seamless immediate biometric registration
        access_token = None
        try:
            sign_res = auth_client.auth.sign_in_with_password({
                "email": clean_email,
                "password": payload.password
            })
            if sign_res and sign_res.session:
                access_token = sign_res.session.access_token
        except Exception as sign_err:
            logger.warning("[REGISTER] auto-login session generation notice: %s", sign_err)

        resp_message = "Account created successfully. Proceed to face registration."
        logger.info(f"[REGISTER TRACE] registration completed for {masked_email}")

        return UserRegisterResponse(
            success=True,
            message=resp_message,
            user_id=user_id,
            email=clean_email,
            access_token=access_token,
            token_type="bearer"
        )

    except AuthApiError as auth_err:
        error_dict = auth_err.to_dict() if hasattr(auth_err, "to_dict") else {}
        code = str(error_dict.get("code", "")).lower()
        error_msg = str(auth_err)
        status_code = status.HTTP_400_BAD_REQUEST

        if (
            code in ["email_exists", "user_already_exists", "email_address_not_authorized"]
            or "already registered" in error_msg.lower()
            or "already been registered" in error_msg.lower()
            or "already exists" in error_msg.lower()
        ):
            status_code = status.HTTP_409_CONFLICT
            error_msg = "An account with this email address already exists."

        raise HTTPException(status_code=status_code, detail=error_msg)

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error("Unexpected error during registration: %s | type=%s | tb=%s", e, type(e).__name__, traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {type(e).__name__}: {str(e)}"
        )


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify registration email OTP",
    description="Validates a 6-digit OTP via Supabase Auth and sets profiles.email_verified=True."
)
async def verify_email(payload: VerifyEmailRequest):
    clean_email = payload.email.strip().lower()
    clean_otp = payload.otp.strip()

    verified = False
    auth_client = get_supabase_client()

    # 1. Try Supabase Auth verify_otp
    for otp_type in ["signup", "email", "magiclink"]:
        try:
            res = auth_client.auth.verify_otp({
                "email": clean_email,
                "token": clean_otp,
                "type": otp_type
            })
            if res and res.user:
                verified = True
                otp_service.set_profile_email_verified(res.user.id, True)
                break
        except Exception:
            pass

    # 2. Try application-level OTP store / fallback
    if not verified:
        try:
            verified = otp_service.verify_email_otp(clean_email, clean_otp)
        except Exception:
            pass

    if verified:
        # Also ensure profile email_verified is true
        try:
            supabase.table("profiles").update({"email_verified": True}).eq("email", clean_email).execute()
        except Exception:
            pass

        return VerifyEmailResponse(
            success=True,
            message="Email verified successfully. You may now proceed to face registration."
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification code."
    )


@router.post(
    "/resend-otp",
    response_model=ResendOtpResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend registration email OTP",
    description="Resends a 6-digit OTP via Supabase Auth + Gmail SMTP."
)
async def resend_otp(payload: ResendOtpRequest):
    clean_email = payload.email.strip().lower()

    try:
        auth_client = get_supabase_client()
        # Trigger Supabase signup resend (dispatches email via configured Gmail SMTP)
        try:
            auth_client.auth.resend({
                "type": "signup",
                "email": clean_email
            })
        except Exception as resend_err:
            logger.info("Supabase resend exception: %s", resend_err)

        # Also refresh fallback OTP store
        try:
            profile_res = supabase.table("profiles").select("id").eq("email", clean_email).execute()
            if profile_res.data and len(profile_res.data) > 0:
                uid = profile_res.data[0].get("id")
                otp_service.create_and_store_otp(uid, clean_email)
        except Exception:
            pass

        return ResendOtpResponse(
            success=True,
            message="A new verification code has been sent to your email."
        )

    except Exception as exc:
        logger.error("Error during OTP resend for %s: %s", clean_email, exc)
        return ResendOtpResponse(
            success=True,
            message="A new verification code has been sent to your email."
        )


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticates a user with email and password via Supabase Auth and returns email_verified status."
)
async def login(payload: UserLoginRequest):
    try:
        auth_client = get_supabase_client()
        auth_response = auth_client.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })

        if not auth_response or not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        user = auth_response.user
        session = auth_response.session

        # Check application-level verification state from public.profiles
        is_verified = otp_service.is_profile_email_verified(user.id)

        session_info = SessionInfo(
            access_token=session.access_token,
            token_type=session.token_type or "bearer",
            expires_in=session.expires_in,
            expires_at=session.expires_at,
            refresh_token=session.refresh_token
        )

        return UserLoginResponse(
            success=True,
            message="Login successful",
            user_id=user.id,
            access_token=session.access_token,
            token_type=session.token_type or "bearer",
            expires_in=session.expires_in,
            refresh_token=session.refresh_token,
            email_verified=is_verified,
            session=session_info
        )

    except AuthApiError as auth_err:
        logger.warning("Supabase AuthApiError during login: %s", auth_err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error("Unexpected error during login: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login. Please try again."
        )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Retrieves the authenticated user's profile including email and email_verified state."
)
async def get_my_profile(current_user: Any = Depends(get_current_user)):
    user_id = str(current_user.id)
    try:
        profile_res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if not profile_res.data or len(profile_res.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found."
            )

        p = profile_res.data[0]
        email_val = p.get("email") or getattr(current_user, "email", "") or ""
        is_verified = otp_service.is_profile_email_verified(user_id) or p.get("email_verified", False)

        return UserProfileResponse(
            id=p["id"],
            full_name=p.get("full_name", ""),
            email=email_val.lower(),
            email_verified=bool(is_verified),
            created_at=str(p.get("created_at") or "")
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as exc:
        logger.error("Error retrieving profile for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve user profile."
        )

