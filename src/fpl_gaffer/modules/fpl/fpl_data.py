from typing import List, Tuple, Dict, Literal

from fpl_gaffer.core.exceptions import FPLAPIError
from fpl_gaffer.modules.fpl.fpl_api import FPLOfficialAPIClient
from fpl_gaffer.utils import build_mappings

DEFAULT_PLAYER_RESULT_LIMIT = 8
MAX_FIXTURE_GAMEWEEKS = 5
DEFAULT_FORM_GAMEWEEKS = 5
MAX_FORM_GAMEWEEKS = 10
MAX_COMPARE_PLAYERS = 5
DEFAULT_DIFFERENTIAL_LIMIT = 8


class FPLDataManager:
    def __init__(self, api: FPLOfficialAPIClient):
        self.api = api

    async def get_gameweek_data(self, include_fixtures: bool = True) -> Dict:
        """Get info for the current gameweek with fixtures and deadline."""
        bootstrap_data, teams, next_gw = await self._fetch_bootstrap_and_next_gw()

        if not bootstrap_data or next_gw is None:
            return {}

        if not include_fixtures:
            return {
                "gameweek": next_gw.get("id") if next_gw else None,
                "deadline": next_gw.get("deadline_time") if next_gw else None,
                "fixtures": None
            }

        # Get fixtures for the current gameweek
        fixtures = await self.api.get_fixtures()

        if not fixtures:
            return {}

        # Filter fixtures for the next gameweek and convert using team mappings
        next_gw_fixtures = []
        if next_gw:
            for fixture in fixtures:
                if fixture.get("event") == next_gw.get("id"):
                    next_gw_fixtures.append({
                        "id": fixture.get("id"),
                        "home_team": teams.get(fixture.get("team_h"), "Unknown"),
                        "away_team": teams.get(fixture.get("team_a"), "Unknown"),
                        "home_team_difficulty": fixture.get("team_h_difficulty", 0),
                        "away_team_difficulty": fixture.get("team_a_difficulty", 0),
                        "kickoff_time": fixture.get("kickoff_time"),
                    })

        return {
            "gameweek": next_gw.get("id") if next_gw else None,
            "deadline": next_gw.get("deadline_time") if next_gw else None,
            "fixtures": next_gw_fixtures
        }

    async def get_fixtures_for_range(self, num_gameweeks: int = 1) -> Dict:
        """Get fixtures from the current gameweek to the next x gameweeks."""
        bootstrap_data, teams, next_gw = await self._fetch_bootstrap_and_next_gw()

        if not bootstrap_data or next_gw is None:
            return {}

        # Get fixtures for the next x gameweeks
        all_fixtures = await self.api.get_fixtures()

        if not all_fixtures:
            return {}

        requested_gameweeks = num_gameweeks
        num_gameweeks = max(1, min(num_gameweeks, MAX_FIXTURE_GAMEWEEKS))

        # Get gameweek range
        start_gw = next_gw.get("id")
        target_gws = set(range(start_gw, start_gw + num_gameweeks))

        upcoming_fixtures = []
        for fixture in all_fixtures:
            if fixture.get("event") in target_gws:
                upcoming_fixtures.append({
                    "id": fixture.get("id"),
                    "gameweek": fixture.get("event"),
                    "home_team": teams.get(fixture.get("team_h"), "Unknown"),
                    "away_team": teams.get(fixture.get("team_a"), "Unknown"),
                    "home_team_difficulty": fixture.get("team_h_difficulty"),
                    "away_team_difficulty": fixture.get("team_a_difficulty"),
                    "kickoff_time": fixture.get("kickoff_time"),
                })

        return {
            "from_gameweek": start_gw,
            "to_gameweek": start_gw + num_gameweeks - 1,
            "requested_gameweeks": requested_gameweeks,
            "capped_at_gameweeks": MAX_FIXTURE_GAMEWEEKS,
            "truncated": requested_gameweeks > num_gameweeks,
            "fixtures": upcoming_fixtures
        }

    @staticmethod
    def _match_players_by_name(all_players: List[Dict], player_names: List[str]) -> List[Dict]:
        """Return bootstrap player rows whose name fields match any of the given queries."""
        query_players = [n.lower() for n in player_names]
        matched = []
        for player in all_players:
            first_name = player.get("first_name", "").lower()
            second_name = player.get("second_name", "").lower()
            web_name = player.get("web_name", "").lower()
            for q in query_players:
                if (q in first_name) or (q in second_name) or (q in web_name):
                    matched.append(player)
                    break
        return matched

    @staticmethod
    def _compact_player(
        player: Dict,
        teams: Dict,
        positions: Dict,
    ) -> Dict:
        """Return the small player shape the agent needs for reasoning."""
        first_name = player.get("first_name", "")
        second_name = player.get("second_name", "")
        name = player.get("web_name") or f"{first_name} {second_name}".strip()

        return {
            "id": player.get("id"),
            "name": name,
            "position": positions.get(player.get("element_type"), "Unknown"),
            "team": teams.get(player.get("team"), "Unknown"),
            "price": player.get("now_cost", 0) / 10,
            "status": player.get("status"),
            "news": player.get("news") or None,
            "chance_of_playing_next_round": player.get("chance_of_playing_next_round"),
            "total_points": player.get("total_points"),
            "form": player.get("form"),
            "selected_by_percent": player.get("selected_by_percent"),
            "minutes": player.get("minutes"),
            "goals_scored": player.get("goals_scored"),
            "assists": player.get("assists"),
            "clean_sheets": player.get("clean_sheets"),
            "expected_goal_involvements": player.get("expected_goal_involvements"),
        }

    @staticmethod
    def _player_sort_key(player: Dict) -> tuple:
        """Sort transfer candidates by stable, useful launch-time signals."""
        def as_float(value, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        return (
            as_float(player.get("total_points")),
            as_float(player.get("form")),
            as_float(player.get("selected_by_percent")),
            as_float(player.get("minutes")),
        )

    async def get_players_by_position(
        self,
        position: Literal["GKP", "DEF", "MID", "FWD"],
        max_price: float
    ) -> Dict:
        """Get players by position and max price."""
        # Get bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if not bootstrap_data:
            return {}

        # Build mappings
        players, teams, positions = build_mappings(bootstrap_data)

        # Find position ID from position short name
        position_id = next((
            pid for pid, pname in positions.items() if pname.lower() == position.lower()
        ), None)

        if position_id is None:
            return {}

        matched_players = []
        for player in bootstrap_data.get("elements", []):
            if (player.get("element_type") == position_id and
                    (player.get("now_cost", 0) / 10) <= max_price):
                matched_players.append(self._compact_player(player, teams, positions))

        matched_players.sort(key=self._player_sort_key, reverse=True)
        selected_players = matched_players[:DEFAULT_PLAYER_RESULT_LIMIT]

        return {
            "position": position,
            "max_price": max_price,
            "count": len(selected_players),
            "total_matches": len(matched_players),
            "truncated": len(matched_players) > len(selected_players),
            "players": selected_players,
        }

    async def get_player_data(self, player_names: List[str]) -> List[Dict]:
        """Get data for specific player(s) by name."""
        # Get bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if not bootstrap_data:
            return []

        _, teams, positions = build_mappings(bootstrap_data)

        # Get all players from bootstrap data
        all_players = bootstrap_data.get("elements", [])
        matched_players = [
            self._compact_player(player, teams, positions)
            for player in self._match_players_by_name(all_players, player_names)
        ]

        return matched_players

    async def get_player_gameweek_history(
        self,
        player_names: List[str],
        num_gameweeks: int = DEFAULT_FORM_GAMEWEEKS,
    ) -> Dict:
        """Get each named player's points/minutes/underlying-stats trend over their last N
        completed gameweeks. Use this to judge current form, not just the season-to-date total."""
        bootstrap_data = await self.api.get_bootstrap_data()

        if not bootstrap_data:
            return {}

        _, teams, positions = build_mappings(bootstrap_data)
        all_players = bootstrap_data.get("elements", [])
        matched = self._match_players_by_name(all_players, player_names)

        num_gameweeks = max(1, min(num_gameweeks, MAX_FORM_GAMEWEEKS))

        players_form = []
        for player in matched:
            compact = self._compact_player(player, teams, positions)
            try:
                summary = await self.api.get_player_summary(player["id"])
            except Exception:
                players_form.append({**compact, "recent_gameweeks": [], "note": "history unavailable"})
                continue

            history = summary.get("history", [])[-num_gameweeks:]
            recent = [
                {
                    "gameweek": gw.get("round"),
                    "opponent": teams.get(gw.get("opponent_team"), "Unknown"),
                    "was_home": gw.get("was_home"),
                    "minutes": gw.get("minutes"),
                    "points": gw.get("total_points"),
                    "goals": gw.get("goals_scored"),
                    "assists": gw.get("assists"),
                    "bonus": gw.get("bonus"),
                    "ict_index": gw.get("ict_index"),
                }
                for gw in history
            ]

            players_form.append({
                **compact,
                "gameweeks_analyzed": len(recent),
                "recent_gameweeks": recent,
            })

        return {
            "requested_gameweeks": num_gameweeks,
            "players": players_form,
            "not_found": [
                n for n in player_names if n.lower() not in {
                    p.get("web_name", "").lower() for p in matched
                }
            ],
        }

    async def compare_players(
        self,
        player_names: List[str],
        num_gameweeks_form: int = DEFAULT_FORM_GAMEWEEKS,
    ) -> Dict:
        """Compare 2-5 named players side by side: season stats plus recent-form averages, so the
        agent can reason about who's the better pick right now rather than only on season totals."""
        if len(player_names) < 2:
            return {"error": "Need at least 2 player names to compare."}

        player_names = player_names[:MAX_COMPARE_PLAYERS]
        bootstrap_data = await self.api.get_bootstrap_data()

        if not bootstrap_data:
            return {}

        _, teams, positions = build_mappings(bootstrap_data)
        all_players = bootstrap_data.get("elements", [])
        matched = self._match_players_by_name(all_players, player_names)

        num_gameweeks_form = max(1, min(num_gameweeks_form, MAX_FORM_GAMEWEEKS))

        comparison = []
        for player in matched:
            compact = self._compact_player(player, teams, positions)
            try:
                summary = await self.api.get_player_summary(player["id"])
                history = summary.get("history", [])[-num_gameweeks_form:]
            except Exception:
                history = []

            if history:
                avg_points = round(sum(gw.get("total_points", 0) for gw in history) / len(history), 2)
                avg_minutes = round(sum(gw.get("minutes", 0) for gw in history) / len(history), 1)
            else:
                avg_points, avg_minutes = None, None

            comparison.append({
                **compact,
                "form_window_gameweeks": len(history),
                "avg_points_recent": avg_points,
                "avg_minutes_recent": avg_minutes,
            })

        return {
            "compared": len(comparison),
            "players": comparison,
            "not_found": [
                n for n in player_names if n.lower() not in {
                    p.get("web_name", "").lower() for p in matched
                }
            ],
        }

    async def get_price_movers(
        self,
        direction: Literal["rising", "falling"] = "rising",
        limit: int = DEFAULT_PLAYER_RESULT_LIMIT,
    ) -> Dict:
        """Get players whose price is currently rising or falling the most, based on this
        gameweek's transfer activity. Useful for timing transfers before a price change."""
        bootstrap_data = await self.api.get_bootstrap_data()

        if not bootstrap_data:
            return {}

        _, teams, positions = build_mappings(bootstrap_data)
        elements = bootstrap_data.get("elements", [])

        def change(p):
            try:
                return float(p.get("cost_change_event", 0))
            except (TypeError, ValueError):
                return 0.0

        if direction == "rising":
            candidates = [p for p in elements if change(p) > 0]
            candidates.sort(key=change, reverse=True)
        else:
            candidates = [p for p in elements if change(p) < 0]
            candidates.sort(key=change)

        limit = max(1, min(limit, DEFAULT_PLAYER_RESULT_LIMIT * 2))
        selected = candidates[:limit]

        movers = []
        for p in selected:
            compact = self._compact_player(p, teams, positions)
            movers.append({
                **compact,
                "price_change_this_event": change(p) / 10,
                "transfers_in_event": p.get("transfers_in_event"),
                "transfers_out_event": p.get("transfers_out_event"),
            })

        return {
            "direction": direction,
            "count": len(movers),
            "total_matches": len(candidates),
            "truncated": len(candidates) > len(movers),
            "players": movers,
        }

    async def get_differential_candidates(
        self,
        position: Literal["GKP", "DEF", "MID", "FWD"],
        max_price: float = 15.0,
        max_ownership_percent: float = 10.0,
        min_form: float = 3.0,
        limit: int = DEFAULT_DIFFERENTIAL_LIMIT,
    ) -> Dict:
        """Find low-ownership players with strong current form/points for a position and budget -
        candidates for a differential pick that isn't showing up in expert-consensus searches.
        Numbers-only signal: the agent should present these as a flagged option, not a mainstream
        recommendation."""
        bootstrap_data = await self.api.get_bootstrap_data()

        if not bootstrap_data:
            return {}

        players, teams, positions = build_mappings(bootstrap_data)
        position_id = next((
            pid for pid, pname in positions.items() if pname.lower() == position.lower()
        ), None)
        if position_id is None:
            return {}

        def as_float(value, default=0.0):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        candidates = []
        for p in bootstrap_data.get("elements", []):
            if p.get("element_type") != position_id:
                continue
            if (p.get("now_cost", 0) / 10) > max_price:
                continue
            if as_float(p.get("selected_by_percent")) > max_ownership_percent:
                continue
            if as_float(p.get("form")) < min_form:
                continue
            candidates.append(p)

        candidates.sort(key=self._player_sort_key, reverse=True)
        selected = candidates[:limit]

        return {
            "position": position,
            "max_price": max_price,
            "max_ownership_percent": max_ownership_percent,
            "min_form": min_form,
            "count": len(selected),
            "total_matches": len(candidates),
            "truncated": len(candidates) > len(selected),
            "players": [self._compact_player(p, teams, positions) for p in selected],
        }

    async def _fetch_bootstrap_and_next_gw(self) -> Tuple[Dict, Dict, Dict]:
        """Internal helper to fetch bootstrap data and next gameweek info."""
        # Fetch bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()

        if not bootstrap_data:
            return {}, {}, {}

        # Build team mappings using fpl_mapper
        _, teams, _ = build_mappings(bootstrap_data)

        # Get next gameweek from bootstrap data
        next_gw = (next((
            gw for gw in bootstrap_data.get("events", []) if gw.get("is_next")
        ), None))

        return bootstrap_data, teams, next_gw
