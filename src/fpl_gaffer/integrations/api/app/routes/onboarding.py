from fastapi import APIRouter, HTTPException

from fpl_gaffer.integrations.api.app.services.database import database_service
from fpl_gaffer.integrations.api.app.services.fpl import fpl_service
from fpl_gaffer.integrations.api.app.utils.phone import normalize_phone_number
from fpl_gaffer.integrations.api.app.utils.schemas import (
    OnboardingRequest,
    OnboardingResponse,
)
from fpl_gaffer.modules.fpl import FPLOfficialAPIClient
from fpl_gaffer.modules.user import FPLUserProfileManager


router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post("/register", response_model=OnboardingResponse)
async def register_user(request: OnboardingRequest) -> OnboardingResponse:
    """Register a WhatsApp user and link their FPL team."""
    full_name = request.name.strip()
    phone = normalize_phone_number(request.phone)

    if not full_name:
        raise HTTPException(status_code=422, detail="Name is required")

    if not phone:
        raise HTTPException(status_code=422, detail="Phone number is required")

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
