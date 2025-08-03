#########################################################
############ TESTING MODULES FOR APPLICATION ############
#########################################################
import asyncio
from fpl_gaffer.tools import FPLOfficialAPI

# Testing FPL API tool
api_tool = FPLOfficialAPI()

async def test_fpl_api():
    print("Testing FPL Official API tool...\n")

    # Fetch current gameweek data
    gameweek_data = await api_tool.get_gameweek_data()
    print("\nCurrent Gameweek Data:", gameweek_data)

if __name__ == "__main__":
    asyncio.run(test_fpl_api())