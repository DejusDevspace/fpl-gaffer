from fpl_gaffer.tools import FPLOfficialAPI
from fpl_gaffer.settings import settings
from httpx import AsyncClient
from typing import Dict, Optional
from datetime import datetime


class FPLUserDataExtractor:
    def __init__(self, api: FPLOfficialAPI, manager_id: int):
        self.base_url = settings.fpl_api_base_url
        self.session = AsyncClient()
        self.api = api
        self.manager_id = manager_id

    async def extract_user_data(self) -> Dict:
        """Get user data from the FPL API."""
        # Get manager data
        manager_data = await self.api.get_manager_data(self.manager_id)
        if not manager_data:
            return {}

        # Get team/squad data and extract info
        squad_data = await self.get_latest_team_data()

        # Build user profile
        user_profile = self.build_user_profile(manager_data, squad_data)

        return user_profile

    async def get_latest_team_data(self) -> Optional[Dict]:
        """Get the most recent team data."""
        # Fetch bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()
        if bootstrap_data is None:
            return {}

        # TODO: Build mappings from bootstrap data using fpl_mapper

        # Get current gameweek from bootstrap data
        # TODO: Remove below and replace with state gameweek data
        # TODO: Optimize below block by using 'next' function
        current_gw = None
        for gw in bootstrap_data.get("events", []):
            if gw["is_current"]:
                current_gw = gw
                break

        # Get the team data for the current gameweek
        team_data = await self.api.get_gameweek_picks(
            self.manager_id,
            current_gw.get("id") if current_gw else None
        )

        # Create structured squad data
        # TODO: Update extraction with updated extraction function
        squad_data = self.extract_squad_info(team_data)
        if squad_data is None:
            return None

        # TODO: Get financial status of the team (ITB, etc)

        return squad_data

    # TODO: Update extraction function to include player details using fpl_mapper
    def extract_squad_info(self, team_data: Dict) -> Dict:
        """Extract detailed squad information."""
        picks = team_data.get("picks", [])

        # Squad information dict
        squad_info = {
            "starting_xi": [],
            "bench": [],
            "captain": None,
            "vice_captain": None,
            "active_chip": team_data.get("active_chip", None)
        }

        # Extract player data from picks
        # TODO: Map player IDs to detailed info using fpl_mapper
        for pick in picks:
            player_info = {
                "player_id": pick["element"],
                "position": pick["position"],
                "multiplier": pick["multiplier"]
            }

            # Get captain and vice captain
            if pick["is_captain"]:
                squad_info["captain"] = pick["element"]
            if pick['is_vice_captain']:
                squad_info['vice_captain'] = pick['element']

            # Sort out starting 11
            if pick["position"] <= 11:
                squad_info["starting_xi"].append(player_info)
            else:
                squad_info["bench"].append(player_info)

        return squad_info

    def build_user_profile(
        self,
        manager_data: Dict,
        squad_data: Dict
    ) -> Dict:
        """Build a user profile from extracted data."""
        if manager_data is None:
            return {}

        # Add manager data to user profile
        user_profile = {
            "manager_id": manager_data.get("id"),
            "team_name": manager_data.get("name"),
            "first_name": manager_data.get("player_first_name"),
            "last_name": manager_data.get("player_last_name"),
            "region": manager_data.get("player_region_name"),
            "overall_rank": manager_data.get("summary_overall_rank"),
            "total_points": manager_data.get("summary_overall_points"),
        }

        # Add squad data to user profile
        if squad_data is not None:
            user_profile.update({
                "current_squad": squad_data,
                "last_updated": datetime.now().isoformat()
            })

        return user_profile

    # TODO: Handle auto subs data for team...