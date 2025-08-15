#########################################################
############ TESTING MODULES FOR APPLICATION ############
#########################################################
import asyncio
from fpl_gaffer.tools import FPLOfficialAPI, FPLNewsSearcher

async def test_fpl_api():
    # Testing FPL API tool
    api_tool = await FPLOfficialAPI.create()
    print("Testing FPL Official API tool...\n")

    # Fetch current gameweek data
    gameweek_data = await api_tool.get_gameweek_data()
    print("\nCurrent Gameweek Data:", gameweek_data)

async def test_news_searcher():
    # Testing FPL News Searcher
    news_searcher = FPLNewsSearcher()
    print("Testing FPL News Searcher tool...\n")

    # Get news documents
    news_docs = await news_searcher.search_news()
    print("\nNews Documents:\n", news_docs)

if __name__ == "__main__":
    # asyncio.run(test_fpl_api())
    asyncio.run(test_news_searcher())
