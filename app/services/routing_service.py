import json
import os
from typing import List, Dict, Optional, Tuple
from config.settings import settings


class RoutingService:
    def __init__(self):
        self.teams_file = os.path.join(os.path.dirname(settings.CATEGORIES_FILE).replace('categories.json', ''), 'support_teams.json')
        self._load_config()

    def _load_config(self):
        if os.path.exists(self.teams_file):
            with open(self.teams_file, 'r') as f:
                config = json.load(f)
                self.teams = config.get('teams', [])
                self.technical_keywords = config.get('technical_keywords', [])
                self.helpline = config.get('helpline', {})
        else:
            self.teams = []
            self.technical_keywords = []
            self.helpline = {
                "number": "1-800-XXX-XXXX",
                "hours": "Mon-Fri 9AM-5PM",
                "email": "support@example.com"
            }

    def is_technical(self, feedback_text: str) -> bool:
        text_lower = feedback_text.lower()
        matches = sum(1 for kw in self.technical_keywords if kw in text_lower)
        return matches >= 2

    def get_technical_response(self) -> str:
        return (
            f"We're sorry you're experiencing technical issues. "
            f"For immediate assistance, please call our support helpline: {self.helpline['number']} "
            f"({self.helpline['hours']}). "
            f"You can also email us at {self.helpline['email']}."
        )

    def _extract_parent(self, category: str) -> str:
        return category.split('.')[0].lower() if '.' in category else category.lower()

    def get_team_for_category(self, category: str) -> Optional[Dict]:
        category_lower = self._extract_parent(category)
        for team in self.teams:
            team_cats = [c.lower() for c in team.get('categories', [])]
            if category_lower in team_cats:
                return team
        return None

    def get_team_for_categories(self, categories: List[str]) -> Tuple[Optional[Dict], str]:
        if not categories:
            return None, ""
        
        top_category = categories[0]
        team = self.get_team_for_category(top_category)
        team_name = team['name'] if team else "Unassigned"
        return team, team_name

    def get_all_teams(self) -> List[Dict]:
        return self.teams

    def get_categories_for_team(self, team_name: str) -> List[str]:
        for team in self.teams:
            if team['name'].lower() == team_name.lower():
                return team.get('categories', [])
        return []


routing_service = RoutingService()