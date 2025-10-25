from typing import Dict, Optional, List, Any

from typer.models import OptionInfo

from fpl_gaffer.settings import settings
from fpl_gaffer.modules.fpl.fpl_api import FPLOfficialAPIClient
from httpx import AsyncClient
from fpl_gaffer.utils import build_mappings, map_player


class FPLTeamDataManger:
    def __init__(self, api: FPLOfficialAPIClient, manager_id: int, gameweek: Optional[int] = None):
        self.base_url = settings.FPL_API_BASE_URL
        self.session = AsyncClient()
        self.api = api
        self.manager_id = manager_id
        self.current_gw = gameweek

    async def _get_bootstrap_data(self):
        """Get bootstrap data from FPL API."""
        return await self.api.get_bootstrap_data()

    async def extract_team_data(self) -> Dict:
        """Get team data for a particular user."""
        team_data = await self.get_latest_team_data()
        return team_data

    async def get_latest_team_data(self) -> Optional[Dict]:
        """Get the most recent team data."""
        # Fetch bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if bootstrap_data is None:
            return {}

        # Build mappings from bootstrap data
        players, teams, positions = build_mappings(bootstrap_data)

        if self.current_gw is None:
            # Get current gameweek from bootstrap data
            current_gw = next((
                gw for gw in bootstrap_data.get("events", []) if gw.get("is_current")
            ), None)
            self.current_gw = current_gw.get("id")

        # Get the team data for the current gameweek
        team_data = await self.api.get_gameweek_picks(
            self.manager_id,
            self.current_gw
        )

        # Create structured squad data
        squad_data = await self.extract_squad_info(team_data, players, teams, positions)
        if squad_data is None:
            return None

        return squad_data

    async def extract_squad_info(
        self,
        team_data: Dict,
        players: Dict,
        teams: Dict,
        positions: Dict
    ) -> Dict:
        """Extract detailed squad information."""
        gw_history = team_data.get("entry_history", {})

        # Squad information
        squad_info = {
            "starting_xi": [],
            "bench": [],
            "captain": None,
            "vice_captain": None,
            "active_chip": team_data.get("active_chip", None),
            "points": gw_history.get("points", 0),
            "total_points": gw_history.get("total_points", 0),
            "rank": gw_history.get("overall_rank", 0),
            "squad_value": gw_history.get("value", 0) / 10,
            "transfers": gw_history.get("event_transfers", 0),
            "transfers_cost": gw_history.get("event_transfers_cost", 0),
            "money_itb": gw_history.get("bank", 0) / 10,
            "history": history_data if (history_data := await self.get_user_history()) else {}
        }

        # Get manager picks from team data
        picks = team_data.get("picks", [])

        # Extract player data from picks
        for pick in picks:
            player_info = map_player(pick["element"], players, teams, positions)
            player_info.update({
                "position_in_team": pick["position"],
                "multiplier": pick["multiplier"]
            })

            # Get captain and vice captain
            if pick["is_captain"]:
                squad_info["captain"] = player_info

            if pick['is_vice_captain']:
                squad_info['vice_captain'] = player_info

            # Sort out starting 11
            if pick["position"] <= 11:
                squad_info["starting_xi"].append(player_info)
            else:
                squad_info["bench"].append(player_info)

        return squad_info

    async def get_user_history(self) -> Dict:
        """Get user history data."""
        history_data = await self.api.get_manager_history(self.manager_id)

        # Get history for the current season (along with chips used)
        # Remove past seasons data
        if "past" in history_data:
            history_data.pop("past", None)

        return history_data

    # TODO: Handle auto subs data for team...

    async def get_transfer_history(self) -> List[Dict[str, Any]]:
        """Get user transfer history."""
        # Get bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if bootstrap_data is None:
            return []

        # Build mappings from bootstrap data
        players, teams, positions = build_mappings(bootstrap_data)

        transfers = await self.api.get_transfer_data(self.manager_id)

        if transfers is None:
            return []

        # transfer_history = []
        # Map player ids to names and teams using mapper
        for t in transfers:
            player_in_id = t.get("element_in")
            player_out_id = t.get("element_out")

            player_in_mapped = map_player(player_in_id, players, teams, positions)
            player_out_mapped = map_player(player_out_id, players, teams, positions)

            t["element_in_name"] = player_in_mapped["name"]
            t["element_out_name"] = player_out_mapped["name"]

        return transfers

    async def get_captain_picks(self) -> List[Dict[str, Any]]:
        """Get user captain picks history"""
        # Get bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if bootstrap_data is None:
            return []

        # Build mappings from bootstrap data
        players, teams, positions = build_mappings(bootstrap_data)

        if self.current_gw is None:
            # Get current gameweek from bootstrap data
            current_gw = next((
                gw for gw in bootstrap_data.get("events", []) if gw.get("is_current")
            ), None)
            self.current_gw = current_gw.get("id")
        # print(current_gw)

        captain_picks = []
        # Get the team data for the gameweeks till present
        for gw in range(1, self.current_gw + 1):
            team_data = await self.api.get_gameweek_picks(self.manager_id, gw)
            # Get picks from team data
            picks = team_data.get("picks", [])

            # Extract player data from picks
            for pick in picks:
                player_info = map_player(pick["element"], players, teams, positions)

                # Get captain and vice captain
                if pick["is_captain"]:
                    player_data = {
                        "gameweek": gw,
                        "player_id": player_info.get("id"),
                        "player_name": player_info.get("name"),
                        "is_vice_captain": False
                    }
                    captain_picks.append(player_data)

                if pick['is_vice_captain']:
                    player_data = {
                        "gameweek": gw,
                        "player_id": player_info.get("id"),
                        "player_name": player_info.get("name"),
                        "is_vice_captain": True
                    }
                    captain_picks.append(player_data)

        return captain_picks
