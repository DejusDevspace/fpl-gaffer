from typing import Dict, Tuple, List

def build_mappings(boostrap_data: Dict) -> Tuple[Dict, Dict, Dict]:
    """Build mappings for players, teams, and positions from bootstrap data."""
    players_mapping = {
        player["id"]: {
            "name": f"{player['first_name']} {player['second_name']}",
            "team_id": player["team"],
            "position_id": player["element_type"],
            "price": player["now_cost"] / 10,
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