import httpx


class FPLOfficialAPI:
    def __init__(self):
        self.base_url = "https://fantasy.premierleague.com/api"
        self.session = httpx.AsyncClient()
