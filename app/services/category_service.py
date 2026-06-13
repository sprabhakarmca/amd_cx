import json
from typing import List, Dict, Any, Optional
from config.settings import settings


class CategoryService:
    def __init__(self):
        self.categories_file = settings.CATEGORIES_FILE
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        import os
        if not os.path.exists(self.categories_file):
            default_data = {
                "taxonomy_version": "1.0",
                "description": "CX taxonomy for NPS feedback classification",
                "categories": [
                    {"name": "delivery", "label": "Delivery Experience", "subcategories": ["late_delivery", "damaged_in_transit"]},
                    {"name": "billing", "label": "Billing & Payments", "subcategories": ["incorrect_charge", "double_charge"]},
                    {"name": "product", "label": "Product Quality", "subcategories": ["material_quality", "durability"]}
                ],
                "few_shot_examples": []
            }
            with open(self.categories_file, 'w') as f:
                json.dump(default_data, f, indent=2)

    def _load_data(self) -> dict:
        with open(self.categories_file, 'r') as f:
            return json.load(f)

    def _save_data(self, data: dict):
        with open(self.categories_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_all(self) -> dict:
        data = self._load_data()
        return {
            "categories": data.get("categories", []),
            "few_shot_examples": data.get("few_shot_examples", [])
        }

    def get_categories(self) -> List[str]:
        data = self._load_data()
        return [c.get("name", "") for c in data.get("categories", [])]

    def get_category_names(self) -> List[str]:
        data = self._load_data()
        return [c.get("name", "") for c in data.get("categories", [])]

    def get_all_subcategories(self) -> Dict[str, List[str]]:
        data = self._load_data()
        result = {}
        for cat in data.get("categories", []):
            result[cat.get("name", "")] = cat.get("subcategories", [])
        return result

    def get_few_shot_examples(self) -> List[Dict[str, Any]]:
        data = self._load_data()
        return data.get("few_shot_examples", [])

    def get_category_count(self) -> int:
        data = self._load_data()
        cats = data.get("categories", [])
        total = 0
        for cat in cats:
            subs = cat.get("subcategories", [])
            total += len(subs) if subs else 1
        return total

    def add_category(self, category: str) -> bool:
        data = self._load_data()
        categories = data.get("categories", [])
        if category.lower() in [c.get("name", "").lower() for c in categories]:
            return False
        categories.append({"name": category, "label": category, "subcategories": []})
        data["categories"] = categories
        self._save_data(data)
        return True

    def update_category(self, old_category: str, new_category: str) -> bool:
        data = self._load_data()
        categories = data.get("categories", [])
        for cat in categories:
            if cat.get("name", "").lower() == old_category.lower():
                cat["name"] = new_category
                cat["label"] = new_category
                self._save_data(data)
                return True
        return False

    def delete_category(self, category: str) -> bool:
        data = self._load_data()
        categories = data.get("categories", [])
        for i, cat in enumerate(categories):
            if cat.get("name", "").lower() == category.lower():
                categories.pop(i)
                data["categories"] = categories
                self._save_data(data)
                return True
        return False


category_service = CategoryService()