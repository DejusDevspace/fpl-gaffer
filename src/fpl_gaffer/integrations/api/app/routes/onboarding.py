from fastapi import APIRouter, HTTPException

from fpl_gaffer.integrations.api.app.services.database import database_service
from fpl_gaffer.integrations.api.app.services.fpl import fpl_service
from fpl_gaffer.integrations.api.app.services.whatsapp import whatsapp_service
from fpl_gaffer.integrations.api.app.utils.phone import normalize_phone_number
from fpl_gaffer.integrations.api.app.utils.schemas import (
    OnboardingRequest,
    OnboardingResponse,
    PhoneVerificationRequest,
    PhoneVerificationResponse,
    TeamVerificationRequest,
    TeamVerificationResponse
)
from fpl_gaffer.modules.fpl import FPLOfficialAPIClient
from fpl_gaffer.modules.user import FPLUserProfileManager


router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

@router.post("/verify-team", response_model=TeamVerificationResponse)
async def verify_team(
    request: TeamVerificationRequest,
) -> TeamVerificationResponse:
    """Verify an FPL team."""
    try:
        async with FPLOfficialAPIClient() as api:
            profile_manager = FPLUserProfileManager(api, request.fpl_id)
            user_data = await profile_manager.extract_user_data(mode="api")

            if not user_data:
                raise HTTPException(status_code=400, detail="Invalid FPL ID")

            # Check if the team is already linked to another user
            existing_user = await fpl_service.get_user_by_fpl_id(request.fpl_id)
            if existing_user:
                raise HTTPException(status_code=409, detail="FPL team is already linked to another user")

            # Concat manager name from first and last names (if available)
            first_name = user_data.get("player_first_name", "")
            last_name = user_data.get("player_last_name", "")
            manager_name = f"{first_name} {last_name}".strip() if first_name or last_name else None

            return TeamVerificationResponse(
                status="success",
                fpl_id=request.fpl_id,
                team_name=user_data.get("name"),
                manager_name=manager_name,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid FPL ID or FPL API unavailable") from exc


@router.post("/request-code", response_model=PhoneVerificationResponse)
async def request_phone_verification(
    request: PhoneVerificationRequest,
) -> PhoneVerificationResponse:
    """Send a verification code before allowing phone-linked onboarding."""
    phone = normalize_phone_number(request.phone)

    if not phone:
        raise HTTPException(status_code=422, detail="Phone number is required")

    sent = await whatsapp_service.start_phone_verification(phone)
    if not sent:
        raise HTTPException(status_code=503, detail="Failed to start phone verification")

    return PhoneVerificationResponse(status="sent", phone=phone)


@router.post("/register", response_model=OnboardingResponse)
async def register_user(request: OnboardingRequest) -> OnboardingResponse:
    """Register a WhatsApp user and link their FPL team."""
    full_name = request.name.strip()
    phone = normalize_phone_number(request.phone)

    if not full_name:
        raise HTTPException(status_code=422, detail="Name is required")

    if not phone:
        raise HTTPException(status_code=422, detail="Phone number is required")

    phone_verified = await whatsapp_service.check_phone_verification(
        phone=phone,
        code=request.verification_code,
    )
    if not phone_verified:
        raise HTTPException(status_code=403, detail="Phone verification required")

    try:
        async with FPLOfficialAPIClient() as api:
            profile_manager = FPLUserProfileManager(api, request.fpl_id)
            team_data = await profile_manager.extract_user_data(mode="api")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid FPL ID or FPL API unavailable") from exc

    if not team_data:
        raise HTTPException(status_code=400, detail="Invalid FPL ID")

    user = await database_service.upsert_user_by_phone(full_name=full_name, phone=phone)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create onboarding user")

    fpl_team_id = await fpl_service.link_fpl_team(
        user_id=user["id"],
        fpl_id=request.fpl_id,
        team_data=team_data,
    )
    if not fpl_team_id:
        raise HTTPException(status_code=500, detail="Failed to link FPL team")

    return OnboardingResponse(
        status="success",
        user_id=user["id"],
        phone=phone,
        fpl_id=request.fpl_id,
        fpl_team_id=fpl_team_id,
        team_name=team_data.get("name"),
    )
