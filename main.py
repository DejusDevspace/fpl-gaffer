#########################################################
############ TESTING MODULES FOR APPLICATION ############
#########################################################
import asyncio
from fpl_gaffer.tools import (
    FPLDataExtractor,
    FPLNewsSearcher,
    FPLUserDataExtractor,
    FPLOfficialAPI
)

async def fpl_data():
    # Testing FPL API tool
    api = FPLOfficialAPI()
    fpl_data_extractor = FPLDataExtractor(api)
    print("Testing FPL Data Extraction tool...\n")

    # Fetch current gameweek data
    gameweek_data = await fpl_data_extractor.get_gameweek_data()
    print("\nNext Gameweek Data:", gameweek_data)

async def news_searcher():
    # Testing FPL News Searcher
    news_searcher = FPLNewsSearcher()
    print("Testing FPL News Searcher tool...\n")

    # Get news documents
    news_docs = await news_searcher.search_news()
    print("\nNews Documents:\n", news_docs)

async def user_data():
    # Testing FPL User Data Extractor
    user_id = 2723529
    api = FPLOfficialAPI()

    user_data_extractor = FPLUserDataExtractor(api, manager_id=user_id)
    print("Testing FPL User Data Extractor tool...\n")

    user_profile = await user_data_extractor.extract_user_data()
    print(f"\nUser Profile for ID {user_id}:\n", user_profile)


if __name__ == "__main__":
    asyncio.run(fpl_data())
    # asyncio.run(news_searcher())
    asyncio.run(user_data())
