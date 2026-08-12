from typing import List
from langchain_core.tools import BaseTool
from fpl_gaffer.tools.news import news_search_tool, get_expert_tips_tool
from fpl_gaffer.tools.user import (
    get_user_team_info_tool, get_user_transfer_history_tool,
    get_user_captain_history_tool, get_league_standings_tool,
)
from fpl_gaffer.tools.fpl import (
    get_players_by_position_tool, get_player_data_tool, get_fixtures_for_range_tool,
    get_player_form_tool, compare_players_tool, get_price_movers_tool,
    get_differential_candidates_tool,
)

TOOLS: List[BaseTool] = [
    news_search_tool,
    get_expert_tips_tool,
    get_user_team_info_tool,
    get_user_transfer_history_tool,
    get_user_captain_history_tool,
    get_league_standings_tool,
    get_players_by_position_tool,
    get_player_data_tool,
    get_fixtures_for_range_tool,
    get_player_form_tool,
    compare_players_tool,
    get_price_movers_tool,
    get_differential_candidates_tool,
]
