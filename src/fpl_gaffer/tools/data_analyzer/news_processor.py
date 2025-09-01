from typing import List, Dict
from langchain.schema import Document
from fpl_gaffer.settings import settings


class FPLNewsProcessor:
    def __init__(self, news_docs: List[Document], user_data: Dict):
        self.news_docs = news_docs
        self.user_data = user_data

    def filter_relevant_news(self) -> List[Document]:
        """Filter news documents to get most relevant news for user's team."""
        relevant_docs = []

        # Extract player names and teams from user's squad
        user_players = []
        user_teams = []

        # Get players and teams from starting XI
        for player in self.user_data["squad_info"]["starting_xi"]:
            user_players.append(player["name"])

            # Add player's team
            if player["team"] not in user_teams:
                user_teams.append(player["team"])

        # Get players and teams from bench
        for player in self.user_data["squad_info"]["bench"]:
            user_players.append(player["name"])

            # Add player's team
            if player["team"] not in user_teams:
                user_teams.append(player["team"])

        # Rank documents based on relevance to user's players and teams
        for doc in self.news_docs:
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

            if relevance_score > 0:
                doc.metadata["relevance_score"] = relevance_score
                relevant_docs.append(doc)

        # Sort documents by relevance score
        return sorted(
            relevant_docs,
            key=lambda x: x.metadata["relevance_score"],
            reverse=True
        )[:settings.max_relevant_news]
