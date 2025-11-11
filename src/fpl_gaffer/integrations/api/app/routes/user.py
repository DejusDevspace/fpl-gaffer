from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path
from typing import Dict
from fpl_gaffer.integrations.api.app.middleware.auth import require_auth
from fpl_gaffer.integrations.api.app.utils.schemas import (
    LinkFPLRequest, SyncFPLRequest, DashboardResponse, LeaguesResponse, LeagueStandingsRequest
)
from fpl_gaffer.modules.fpl import FPLOfficialAPIClient
from fpl_gaffer.modules.user import FPLUserProfileManager, FPLTeamDataManger
from fpl_gaffer.integrations.api.app.services.fpl import fpl_service
from fpl_gaffer.integrations.api.app.utils.logger import logger


router = APIRouter(prefix="/api/user", tags=["user"])


@router.post("/link-fpl")
async def link_fpl_team(
    request: LinkFPLRequest,
    current_user: Dict = Depends(require_auth),
):
    """
    Link user's FPL team to their account.

    Expected request body:
    {
        "fpl_id": 123456
    }
    """
    user_id = current_user["sub"]

    # Get user/team data
    api = FPLOfficialAPIClient()
    profile_manager = FPLUserProfileManager(api, request.fpl_id)
    user_data = await profile_manager.extract_user_data(mode="api")

    fpl_team_id = await fpl_service.link_fpl_team(
        user_id=user_id,
        fpl_id=request.fpl_id,
        team_data=user_data
    )

    if not fpl_team_id:
        raise HTTPException(status_code=500, detail="Failed to link FPL team")

    return {
        "status": "success",
        "message": "FPL team linked successfully",
        "fpl_team_id": fpl_team_id
    }


@router.post("/sync-fpl")
async def sync_fpl_data(
    request: SyncFPLRequest,
    current_user: Dict = Depends(require_auth),
):
    """
    Sync all FPL data for user's team.

    Expected request body:
    {
        "fpl_id": 123456
    }
    """
    user_id = current_user["sub"]

    # Get user's FPL team
    fpl_team = await fpl_service.get_user_fpl_team(user_id)

    if not fpl_team:
        raise HTTPException(status_code=404, detail="FPL team not linked. Please link your FPL team first.")

    fpl_team_id = fpl_team["id"]
    fpl_id = fpl_team["fpl_id"]

    # TODO: Check error handling below for necessary refactor
    if fpl_id != request.fpl_id:
        raise HTTPException(
            status_code=404,
            detail="FPL ID does not match linked FPL team. Please link team or use correct FPL ID."
        )

    # Get team, gw history, transfer history, and captain picks data
    # TEAM DATA
    async with FPLOfficialAPIClient() as api:
        profile_manager = FPLUserProfileManager(api, request.fpl_id)
        team_data = await profile_manager.extract_user_data(mode="api")

    # GAMEWEEK HISTORY
    async with FPLOfficialAPIClient() as api:
        data_manager = FPLTeamDataManger(api, request.fpl_id)
        gameweek_history = await data_manager.get_user_history()

    # TRANSFER HISTORY
    async with FPLOfficialAPIClient() as api:
        data_manager = FPLTeamDataManger(api, request.fpl_id)
        transfer_history = await data_manager.get_transfer_history()

    # CAPTAIN PICKS
    async with FPLOfficialAPIClient() as api:
        data_manager = FPLTeamDataManger(api, request.fpl_id)
        captain_picks = await data_manager.get_captain_picks()

    # LEAGUES DATA
    # TODO: Get leagues data
    async with FPLOfficialAPIClient() as api:
        data_manager = FPLTeamDataManger(api, request.fpl_id)
        leagues_data = await data_manager.get_user_leagues()

    # Update team data
    await fpl_service.link_fpl_team(user_id, fpl_id, team_data)

    # Sync all data
    await fpl_service.sync_gameweek_history(fpl_team_id, gameweek_history)
    await fpl_service.sync_transfer_history(fpl_team_id, transfer_history)
    await fpl_service.sync_captain_picks(fpl_team_id, captain_picks)
    # TODO: Sync leagues data
    await fpl_service.sync_user_leagues(fpl_team_id, leagues_data)

    logger.info(f"FPL data synced for user {user_id}")

    return {
        "status": "success",
        "message": "FPL data synced successfully"
    }


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Dict = Depends(require_auth),
):
    """Get all dashboard data for authenticated user."""
    user_id = current_user["sub"]

    dashboard_data = await fpl_service.get_dashboard_data(user_id)

    if not dashboard_data:
        raise HTTPException(
            status_code=404,
            detail="FPL team not linked or no data available. Please link your FPL team and sync data."
        )

    return DashboardResponse(**dashboard_data)


@router.get("/leagues", response_model=LeaguesResponse)
async def get_leagues(
    current_user: Dict = Depends(require_auth)
):
    """Get all leagues for authenticated user."""
    user_id = current_user["sub"]

    # Get user's leagues from database
    leagues_data = await fpl_service.get_user_leagues(user_id)

    if leagues_data is None:
        raise HTTPException(
            status_code=404,
            detail="FPL team not linked. Please link your FPL team first."
        )

    return LeaguesResponse(**leagues_data)


@router.get("/leagues/classic/{league_id}/standings")
async def get_classic_league_standings(
    # request: LeagueStandingsRequest,
    league_id: int = Path(...),
    page: int = Query(1, ge=1),
    current_user: Dict = Depends(require_auth)
):
    """
    Get the standings for a specific league.

    Expected request body:
    {
        "league_id": 123456,
        "page": 1
    }
    """
    user_id = current_user["sub"]

    # Get user's FPL team
    fpl_team = await fpl_service.get_user_fpl_team(user_id)

    if not fpl_team:
        raise HTTPException(status_code=404, detail="FPL team not linked. Please link your FPL team first.")

    fpl_id = fpl_team["fpl_id"]
    async with FPLOfficialAPIClient() as api:
        data_manager = FPLTeamDataManger(api, fpl_id)
        standings = await data_manager.get_league_standings(league_id, page)

    if not standings:
        raise HTTPException(
            status_code=404,
            detail="League not found."
        )

    return {
        "status": "success",
        "standings": standings
    }


@router.get("/fpl-team")
async def get_fpl_team(
    current_user: Dict = Depends(require_auth),
):
    """Get user's linked FPL team info."""
    user_id = current_user["sub"]

    fpl_team = await fpl_service.get_user_fpl_team(user_id)

    if not fpl_team:
        raise HTTPException(status_code=404, detail="FPL team not linked")

    return fpl_team


@router.delete("/unlink-fpl")
async def unlink_fpl_team(
    current_user: Dict = Depends(require_auth),
):
    """Unlink user's FPL team (deletes all FPL data)."""
    user_id = current_user["sub"]

    try:
        fpl_service.client.table("fpl_teams").delete().eq("user_id", user_id).execute()
        return {"status": "success", "message": "FPL team unlinked"}
    except Exception as e:
        logger.error(f"Error unlinking FPL team: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to unlink FPL team")
