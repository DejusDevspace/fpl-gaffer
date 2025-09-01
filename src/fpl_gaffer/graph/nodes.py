from fpl_gaffer.core.state import WorkflowState
from fpl_gaffer.tools import (
    FPLOfficialAPI,
    FPLNewsSearcher,
    FPLDataExtractor,
    FPLUserDataExtractor
)


async def fetch_fpl_data_node(state: WorkflowState) -> WorkflowState:
    """Fetch FPL data for the next gameweek."""
    api = FPLOfficialAPI()
    fpl_data_extractor = FPLDataExtractor(api)

    try:
        # Fetch gameweek relevant data
        gameweek_data = await fpl_data_extractor.get_gameweek_data()

        if gameweek_data is None:
            state.error_log.append("No gameweek data found.")
            return state

        # Update state with gameweek data
        state.gameweek = gameweek_data.get("gameweek")
        state.deadline = gameweek_data.get("deadline")
        state.fpl_data.update(gameweek_data)

    except Exception as e:
        state.error_log.append(f"Error fetching FPL data: {e}")

    return state

async def fetch_user_data_node(state: WorkflowState, manager_id: int) -> WorkflowState:
    """Fetch user data."""
    api = FPLOfficialAPI()
    # TODO: Get manager ID from state or from config (save in db or?)
    user_data_extractor = FPLUserDataExtractor(api, manager_id)

    try:
        # Fetch manager data
        user_data = await user_data_extractor.extract_user_data()

        if user_data is None:
            state.error_log.append(f"No manager data found for ID {manager_id}.")
            return state

        # Update state with manager data
        state.user_data = user_data

    except Exception as e:
        state.error_log.append(f"Error fetching user data: {e}")

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
