from typing import List, Dict
from langchain.schema import Document
from fpl_gaffer.settings import settings


class FPLNewsProcessor:
    def __init__(self, news_docs: List[Document], user_data: Dict):
        self.news_docs = news_docs
        self.user_data = user_data
        self.user_players = self._get_user_players()
        self.user_teams = self._get_user_teams()

    def filter_relevant_news(self) -> List[Document]:
        """Filter news documents to get most relevant news for user's team."""
        relevant_docs = []

        # Rank documents based on relevance to user's players and teams
        for doc in self.news_docs:
            relevance_score = self._calculate_relevance_score(
                doc,
                self.user_players,
                self.user_teams
            )

            if relevance_score > 0:
                doc.metadata["relevance_score"] = relevance_score
                relevant_docs.append(doc)

        # Sort documents by relevance score
        return sorted(
            relevant_docs,
            key=lambda x: x.metadata["relevance_score"],
            reverse=True
        )[:settings.max_relevant_news]

    def _calculate_relevance_score(
        self,
        doc: Document,
        user_players: List,
        user_teams: List
    ) -> int:
        """Calculate relevance score for a document based on user data."""
        relevance_score = 0

        # Check for player mentions
        for player in user_players:
            if player.lower() in doc.page_content.lower():
                relevance_score += settings.user_player_relevance_score

        # Check for team mentions
        for team in user_teams:
            if team.lower() in doc.page_content.lower():
                relevance_score += settings.user_team_relevance_score

        # Always include general FPL advice
        if doc.metadata.get("category") == "fpl":
            relevance_score += settings.fpl_news_relevance_score

        return relevance_score

    def _get_user_players(self) -> List[str]:
        """Extract player names from user's squad."""
        if not self.user_data or "squad_info" not in self.user_data:
            return []

        players = []
        # Get players from starting XI
        for player in self.user_data["squad_info"].get("starting_xi", []):
            players.append(player["name"])

        # Get players from bench
        for player in self.user_data["squad_info"].get("bench", []):
            players.append(player["name"])

        return players

    def _get_user_teams(self) -> List[str]:
        """Extract team names from user's squad."""
        if not self.user_data or "squad_info" not in self.user_data:
            return []

        teams = set()
        # Get teams from starting XI
        for player in self.user_data["squad_info"].get("starting_xi", []):
            teams.add(player["team"])

        # Get teams from bench
        for player in self.user_data["squad_info"].get("bench", []):
            teams.add(player["team"])

        return list(teams)
