import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.services.database import db


class ReviewService:
    def create_review(
        self,
        feedback_id: str,
        feedback_text: str,
        product: str,
        nps_score: int,
        categories: List[str],
        assigned_team: str,
        original_response: str,
        user_id: Optional[str] = None,
        is_technical: bool = False,
        duplicate_note: str = None,
        intent_note: str = None
    ) -> str:
        review_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO reviews (review_id, feedback_id, feedback_text, product, nps_score, "
            "categories, assigned_team, user_id, created_at, is_technical, "
            "original_response, duplicate_note, intent_note) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [review_id, feedback_id or "", feedback_text, product or "Unknown", nps_score,
             ",".join(categories) if categories else "", assigned_team or "Unassigned",
             user_id or "anonymous", datetime.now().isoformat(),
             1 if is_technical else 0, original_response or "",
             duplicate_note or "", intent_note or ""]
        )
        return review_id

    def _row_to_dict(self, r) -> Dict[str, Any]:
        return {
            "id": r["review_id"],
            "feedback_text": r["feedback_text"],
            "product": r["product"],
            "nps_score": r["nps_score"],
            "categories": r["categories"].split(",") if r.get("categories") else [],
            "assigned_team": r["assigned_team"],
            "status": r["status"],
            "user_id": r["user_id"],
            "created_at": r["created_at"],
            "is_technical": bool(r["is_technical"]),
            "duplicate_note": r.get("duplicate_note", ""),
            "intent_note": r.get("intent_note", ""),
            "original_response": r.get("original_response", ""),
            "notes": r.get("notes", ""),
            "final_response": r.get("final_response", ""),
            "feedback_id": r.get("feedback_id", "")
        }

    def get_pending_reviews(self, team_filter: str = None, category_filter: str = None) -> List[Dict[str, Any]]:
        conditions = ["status=%s"]
        params = ["pending"]
        if team_filter:
            conditions.append("assigned_team=%s")
            params.append(team_filter)
        rows = db.fetchall(
            f"SELECT * FROM reviews WHERE {' AND '.join(conditions)} ORDER BY created_at DESC",
            params
        )
        results = []
        for r in rows:
            if category_filter:
                cats = (r.get("categories") or "").split(",")
                if category_filter.lower() not in [c.lower() for c in cats]:
                    continue
            results.append(self._row_to_dict(r))
        return results

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        r = db.fetchone("SELECT * FROM reviews WHERE review_id=%s", [review_id])
        return self._row_to_dict(r) if r else None

    def update_review(
        self,
        review_id: str,
        action: str,
        notes: str = None,
        final_response: str = None
    ) -> bool:
        r = db.fetchone("SELECT * FROM reviews WHERE review_id=%s", [review_id])
        if not r:
            return False

        if action == "add_notes" and notes:
            current = (r["notes"] or "")
            new_notes = current + f"\n[{datetime.now().isoformat()}] {notes}"
            db.execute("UPDATE reviews SET notes=%s WHERE review_id=%s", [new_notes, review_id])
        elif action == "send_followup" and final_response:
            db.execute("UPDATE reviews SET final_response=%s, status=%s WHERE review_id=%s",
                       [final_response, "resolved", review_id])
        elif action == "resolve":
            db.execute("UPDATE reviews SET status=%s WHERE review_id=%s", ["resolved", review_id])
        elif action == "reopen":
            db.execute("UPDATE reviews SET status=%s WHERE review_id=%s", ["pending", review_id])
        return True

    def get_all_reviews(self, team_filter: str = None) -> List[Dict[str, Any]]:
        if team_filter:
            rows = db.fetchall(
                "SELECT * FROM reviews WHERE assigned_team=%s ORDER BY created_at DESC",
                [team_filter]
            )
        else:
            rows = db.fetchall("SELECT * FROM reviews ORDER BY created_at DESC")
        return [self._row_to_dict(r) for r in rows]

    def get_all_teams_from_reviews(self) -> List[str]:
        rows = db.fetchall("SELECT DISTINCT assigned_team FROM reviews WHERE assigned_team != %s AND assigned_team IS NOT NULL AND assigned_team != %s", ["", ""])
        return [r["assigned_team"] for r in rows]


review_service = ReviewService()
