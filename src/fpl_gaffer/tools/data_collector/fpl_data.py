from fpl_gaffer.tools import FPLOfficialAPI

class FPLDataExtractor:
    def __init__(self, api: FPLOfficialAPI):
        self.api = api

    async def get_gameweek_data(self):
        """Get info for the current gameweek and deadline."""
        # Fetch bootstrap data
        bootstrap_data = await self.api.get_bootstrap_data()
        if bootstrap_data is None:
            return {}

        # Get next gameweek from bootstrap data
        # TODO: Optimize below block by using 'next' function
        next_gw = None
        for gw in bootstrap_data.get("events", []):
            if gw["is_next"]:
                next_gw = gw
                break

        # Get fixtures for the current gameweek
        fixtures = await self.api.get_fixtures()
        if not fixtures:
            return {}

        # Filter fixtures for the next gameweek
        next_gw_fixtures = [
            fixture for fixture in fixtures if fixture.get("event") == next_gw.get("id")
        ] if next_gw else []

        return {
            "gameweek": next_gw.get("id") if next_gw else None,
            "deadline": next_gw.get("deadline_time") if next_gw else None,
            "finished": next_gw.get("finished") if next_gw else False,
            "fixtures": next_gw_fixtures
        }
