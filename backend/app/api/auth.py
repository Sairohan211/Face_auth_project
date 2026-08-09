import logging
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
    description="Registers a user account, sets email_verified=False, generates a secure 6-digit OTP, and sends it via Resend."
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
        # 1. Create the user in Supabase Auth
        # Note: Set email_confirm=True at Supabase layer so Supabase Auth does not send its own built-in email.
        # Application-level email verification is managed via public.profiles.email_verified.
        auth_response = supabase.auth.admin.create_user({
            "email": clean_email,
            "password": payload.password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": clean_name
            }
        })

        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed in authentication service."
            )

        user_id = auth_response.user.id

        # 2. Store profile in public.profiles with email and email_verified = false
        try:
            try:
                supabase.table("profiles").insert({
                    "id": user_id,
                    "full_name": clean_name,
                    "email": clean_email,
                    "email_verified": False
                }).execute()
            except Exception as ins_err:
                logger.warning("Primary profile insert with email_verified failed, retrying without email_verified: %s", ins_err)
                supabase.table("profiles").insert({
                    "id": user_id,
                    "full_name": clean_name,
                    "email": clean_email
                }).execute()
            otp_service.set_profile_email_verified(user_id, False)
            logger.warning(f"[REGISTER TRACE] profile created for {masked_email}")

        except Exception as db_err:
            logger.error("Failed to insert profile for user %s: %s", user_id, db_err)
            # Rollback auth account to prevent orphaned records
            try:
                supabase.auth.admin.delete_user(user_id)
            except Exception as rollback_err:
                logger.error("Rollback failed for user %s: %s", user_id, rollback_err)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User account could not be initialized in database."
            )


        # 3. Generate secure 6-digit OTP, store only the cryptographic hash, and send via Gmail SMTP
        email_sent = False
        email_error = None
        try:
            raw_otp = otp_service.create_and_store_otp(user_id, clean_email)
            logger.info(f"[REGISTER TRACE] OTP generated for {masked_email}")
            logger.info(f"[REGISTER TRACE] OTP hash stored for {masked_email}")
            
            logger.info(f"[REGISTER TRACE] calling Gmail SMTP email service for {masked_email}")
            email_sent, email_error = email_service.send_verification_otp_email(
                recipient_email=clean_email,
                recipient_name=clean_name,
                otp=raw_otp
            )
            if email_sent:
                logger.info(f"[REGISTER TRACE] email service returned success for {masked_email}")
            else:
                logger.warning(f"[REGISTER TRACE] email service returned failure for {masked_email}: {email_error}")
        except Exception as otp_gen_err:
            email_error = str(otp_gen_err)
            logger.error("Failed to generate or dispatch OTP for %s: %s", clean_email, email_error)
            logger.warning(f"[REGISTER TRACE] email service returned failure for {masked_email}: {email_error}")

        if email_sent:
            resp_message = "Account created successfully. A verification code has been sent to your email."
        else:
            resp_message = f"Account created successfully. However, OTP email delivery failed: {email_error or 'Unknown delivery error'}."

        logger.info(f"[REGISTER TRACE] registration completed for {masked_email}")

        return UserRegisterResponse(
            success=True,
            message=resp_message,
            user_id=user_id,
            email=clean_email
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
        logger.error("Unexpected error during registration: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration. Please try again."
        )


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify registration email OTP",
    description="Validates a 6-digit OTP against stored cryptographic hash and sets profiles.email_verified=True."
)
async def verify_email(payload: VerifyEmailRequest):
    try:
        otp_service.verify_email_otp(payload.email, payload.otp)
        return VerifyEmailResponse(
            success=True,
            message="Email verified successfully. You may now proceed to face registration."
        )
    except otp_service.InvalidOTPError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code."
        )
    except Exception as exc:
        logger.error("Error during OTP verification for %s: %s", payload.email, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code."
        )


@router.post(
    "/resend-otp",
    response_model=ResendOtpResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend registration email OTP",
    description="Generates a new 6-digit OTP, invalidates previous OTP, enforces 60s cooldown, and delivers via Gmail SMTP."
)
async def resend_otp(payload: ResendOtpRequest):
    clean_email = payload.email.strip().lower()

    try:
        # Check user existence and name
        user_id = None
        user_name = "User"
        try:
            # Query profiles table or auth users
            profile_res = supabase.table("profiles").select("id, full_name").eq("email", clean_email).execute()
            if profile_res.data and len(profile_res.data) > 0:
                user_id = profile_res.data[0].get("id")
                user_name = profile_res.data[0].get("full_name") or "User"
        except Exception:
            pass

        if not user_id:
            # Try finding user via admin auth list
            try:
                users_list = supabase.auth.admin.list_users()
                for u in users_list:
                    if u.email and u.email.lower() == clean_email:
                        user_id = u.id
                        user_name = (u.user_metadata or {}).get("full_name", "User")
                        break
            except Exception:
                pass

        if not user_id:
            # Generic response to avoid leaking account existence
            return ResendOtpResponse(
                success=True,
                message="A new verification code has been sent."
            )

        # Generate new OTP (raises OTPCooldownError if cooldown is active)
        raw_otp = otp_service.create_and_store_otp(user_id, clean_email)
        sent, err = email_service.send_verification_otp_email(
            recipient_email=clean_email,
            recipient_name=user_name,
            otp=raw_otp
        )
        if not sent:
            logger.warning(f"Resend OTP email delivery failed for {clean_email}: {err}")

        return ResendOtpResponse(
            success=True,
            message="A new verification code has been sent."
        )

    except otp_service.OTPCooldownError as cd_err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(cd_err)
        )
    except Exception as exc:
        logger.error("Error during OTP resend for %s: %s", clean_email, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not resend verification code. Please try again."
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

