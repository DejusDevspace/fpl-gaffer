from typing import Dict, Any, List, Optional
import datetime as dt
from datetime import datetime
from fpl_gaffer.integrations.api.app.services.supabase import supabase_client
from fpl_gaffer.integrations.api.app.utils.logger import logger


class FPLService:
    """
    Service for FPL data operations.
    """

    def __init__(self):
        self.client = supabase_client.client

    async def link_fpl_team(self, user_id: str, fpl_id: int, team_data: Dict[str, Any]) -> Optional[str]:
        """
        Link an FPL team to a user account.

        Args:
            user_id: Supabase user ID
            fpl_id: FPL team ID
            team_data: Team data dictionary from FPL API client

        Returns:
            fpl_team_id if successful, None otherwise
        """
        try:
            # TODO: Expand to add other info
            data = {
                "user_id": user_id,
                "fpl_id": fpl_id,
                "team_name": team_data.get("name"),
                "player_first_name": team_data.get("player_first_name"),
                "player_last_name": team_data.get("player_last_name"),
                "years_active": team_data.get("years_active"),  # added
                "favourite_team": team_data.get("favourite_team"),  # added
                "started_event": team_data.get("started_event"),   # added
                "overall_rank": team_data.get("summary_overall_rank"),
                "overall_points": team_data.get("summary_overall_points"),
                "current_gameweek": team_data.get("current_event"),
                "total_transfers": team_data.get("last_deadline_total_transfers", 0),
                "team_value": team_data.get("last_deadline_value"),
                "bank": team_data.get("last_deadline_bank"),
                "last_synced_at": datetime.now(dt.timezone.utc),
            }

            result = self.client.table("fpl_teams").upsert(data, on_conflict="fpl_id").execute()

            if result.data and len(result.data) > 0:
                logger.info(f"FPL team {fpl_id} linked to user {user_id}")
                return result.data[0]["id"]
            return None

        except Exception as e:
            logger.error(f"Error linking FPL team: {str(e)}")
            return None

    async def sync_gameweek_history(self, fpl_team_id: str, history_data: Dict[str, Any]) -> bool:
        """
        Sync gameweek history data.

        Args:
            fpl_team_id: FPL team UUID
            history_data: User history data from FPL API client

        Returns:
            True if successful, False otherwise
        """
        try:
            records = []
            for gw in history_data.get("current"):
                records.append({
                    "fpl_team_id": fpl_team_id,
                    "gameweek": gw["event"],
                    "points": gw["points"],
                    "total_points": gw["total_points"],
                    "rank": gw.get("rank"),
                    "rank_sort": gw.get("rank_sort"),  # added
                    "overall_rank": gw.get("overall_rank"),
                    "percentile_rank": gw.get("percentile_rank"),
                    "bank": gw.get("bank"),
                    "team_value": gw.get("value"),
                    "event_transfers": gw.get("event_transfers", 0),
                    "event_transfers_cost": gw.get("event_transfers_cost", 0),
                    "points_on_bench": gw.get("points_on_bench", 0),
                })

            # Batch upsert
            self.client.table("gameweek_history").upsert(records, on_conflict="fpl_team_id,gameweek").execute()
            logger.info(f"Synced {len(records)} gameweek records for team {fpl_team_id}")
            return True

        except Exception as e:
            logger.error(f"Error syncing gameweek history: {str(e)}")
            return False

    async def sync_transfer_history(self, fpl_team_id: str, transfers_data: List[Dict[str, Any]]) -> bool:
        """
        Sync transfer history data.

        Args:
            fpl_team_id: FPL team UUID
            transfers_data: List of transfers from FPL API client

        Returns:
            True if successful, False otherwise
        """
        try:
            records = []
            for transfer in transfers_data:
                records.append({
                    "fpl_team_id": fpl_team_id,
                    "gameweek": transfer["gameweek"],
                    "time": transfer.get("time"),
                    "player_in_id": transfer.get("player_in_id"),
                    "player_in_name": transfer.get("player_in_name"),
                    "player_in_cost": transfer.get("player_in_cost"),
                    "player_out_id": transfer.get("player_out_id"),
                    "player_out_name": transfer.get("player_out_name"),
                    "player_out_cost": transfer.get("player_out_cost"),
                })

            # Clear existing and insert new
            self.client.table("transfer_history").delete().eq("fpl_team_id", fpl_team_id).execute()

            if records:
                self.client.table("transfer_history").insert(records).execute()

            logger.info(f"Synced {len(records)} transfer records for team {fpl_team_id}")
            return True

        except Exception as e:
            logger.error(f"Error syncing transfer history: {str(e)}")
            return False

    async def sync_captain_picks(self, fpl_team_id: str, captains_data: List[Dict[str, Any]]) -> bool:
        """
        Sync captain picks data.

        Args:
            fpl_team_id: FPL team UUID
            captains_data: List of captain picks from FPL API client

        Returns:
            True if successful, False otherwise
        """
        try:
            records = []
            for pick in captains_data:
                records.append({
                    "fpl_team_id": fpl_team_id,
                    "gameweek": pick["gameweek"],
                    "player_id": pick.get("player_id"),
                    "player_name": pick.get("player_name"),
                    "is_vice_captain": pick.get("is_vice_captain", False),
                })

            # Clear existing and insert new
            self.client.table("captain_picks").delete().eq("fpl_team_id", fpl_team_id).execute()
            if records:
                self.client.table("captain_picks").insert(records).execute()

            logger.info(f"Synced {len(records)} captain picks for team {fpl_team_id}")
            return True

        except Exception as e:
            logger.error(f"Error syncing captain picks: {str(e)}")
            return False

    async def get_user_fpl_team(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's linked FPL team."""
        try:
            result = self.client.table("fpl_teams").select("*").eq("user_id", user_id).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]

            return None

        except Exception as e:
            logger.error(f"Error getting user FPL team: {str(e)}")
            return None

    async def get_dashboard_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get all dashboard data for a user.

        Returns:
            {
                "team": {...},
                "current_gameweek": {...},
                "gameweek_history": [...],
                "transfer_history": [...],
                "current_captain": {...}
            }
        """
        try:
            # Get FPL team
            fpl_team = await self.get_user_fpl_team(user_id)

            if not fpl_team:
                return None

            fpl_team_id = fpl_team["id"]
            current_gw = fpl_team["current_gameweek"]

            # Get current gameweek data
            current_gw_data = self.client.table("gameweek_history") \
                .select("*") \
                .eq("fpl_team_id", fpl_team_id) \
                .eq("gameweek", current_gw) \
                .execute()

            # Get all gameweek history
            gw_history = self.client.table("gameweek_history") \
                .select("*") \
                .eq("fpl_team_id", fpl_team_id) \
                .order("gameweek") \
                .execute()

            # Get transfer history
            transfers = self.client.table("transfer_history") \
                .select("*") \
                .eq("fpl_team_id", fpl_team_id) \
                .order("gameweek") \
                .execute()

            # Get current captain
            captain = self.client.table("captain_picks") \
                .select("*") \
                .eq("fpl_team_id", fpl_team_id) \
                .eq("gameweek", current_gw) \
                .eq("is_vice_captain", False) \
                .execute()

            return {
                "team": fpl_team,
                "current_gameweek": current_gw_data.data[0] if current_gw_data.data else None,
                "gameweek_history": gw_history.data or [],
                "transfer_history": transfers.data or [],
                "current_captain": captain.data[0] if captain.data else None,
            }

        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            return None

fpl_service = FPLService()
