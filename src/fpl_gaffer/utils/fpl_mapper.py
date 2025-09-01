from typing import Dict, Tuple, List

def build_mappings(boostrap_data: Dict) -> Tuple[Dict, Dict, Dict]:
    """Build mappings for players, teams, and positions from bootstrap data."""
    players_mapping = {
        player["id"]: {
            "name": f"{player['first_name']} {player['second_name']}",
            "team_id": player["team"],
            "position_id": player["element_type"],
            "current_price": player["now_cost"] / 10,
            "status": player["status"],
        }
        for player in boostrap_data.get("elements", [])
    }

    teams_mapping = {
        team["id"]: team["name"]
        for team in boostrap_data.get("teams", [])
    }

    positions_mapping = {
        position["id"]: position["singular_name_short"]
        for position in boostrap_data.get("element_types", [])
    }

    return players_mapping, teams_mapping, positions_mapping

def map_player(
    player_id: int,
    players: Dict,
    teams: Dict,
    positions: Dict
) -> Dict:
    """Map a player ID to detailed player information."""
    player_info = players.get(player_id, {})

    if not player_info:
        return {}

    return {
        "id": player_id,
        "name": player_info["name"],
        "team": teams.get(player_info["team_id"], "Unknown Team"),
        "position": positions.get(player_info["position_id"], "Unknown Position"),
        "current_price": player_info["current_price"],
        "status": player_info["status"]
    }

def map_squad(
    picks: Dict,
    players: Dict,
    teams: Dict,
    positions: Dict
) -> List[Dict]:
    """
    Map a list of player IDs to detailed player information.
    Expects 'picks' data from FPLOfficialAPI.get_gameweek_picks()
    """
    mapped_team = []

    for pick in picks:
        mapped_team.append({
            **map_player(pick["element"], players, teams, positions),
            "multiplier": pick["multiplier"],
            "is_captain": pick.get("is_captain", False),
            "is_vice_captain": pick.get("is_vice_captain", False),
        })

    return mapped_team