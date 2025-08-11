from fpl_gaffer.core.state import WorkflowState
from fpl_gaffer.tools import FPLOfficialAPI, FPLNewsSearcher

async def fetch_fpl_data_node(state: WorkflowState) -> WorkflowState:
    """Fetch FPL data from the FPL Official API."""
    fpl_api = FPLOfficialAPI()
    try:
        # Fetch gameweek relevant data
        gameweek_data = await fpl_api.get_gameweek_data()

        if not gameweek_data:
            state.error_log.append("No gameweek data found.")
            return state

        # Update state with gameweek data
        state.gameweek = gameweek_data.get("gameweek")
        state.deadline = gameweek_data.get("deadline")
        state.fpl_api_data.update(gameweek_data)

    except Exception as e:
        state.error_log.append(f"Error fetching FPL data: {e}")

    return state

async def search_news_node(state: WorkflowState) -> WorkflowState:
    """Search for news data using the news searcher tool."""
    news_searcher = FPLNewsSearcher()
    try:
        # Search for news
        news_docs = await news_searcher.search_news()

        if not news_docs:
            state.error_log.append("No news documents found.")
            return state

        # Update state with news documents
        state.news_search_data.extend(news_docs)

    except Exception as e:
        state.error_log.append(f"Error searching news: {e}")

    return state
