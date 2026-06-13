from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from app.services.review_service import review_service
from app.services.routing_service import routing_service
from app.services.vector_store import vector_store

router = APIRouter(prefix="/api", tags=["reviews"])


class ReviewUpdateRequest(BaseModel):
    action: str = Field(..., description="Action: add_notes, send_followup, resolve, reopen")
    notes: Optional[str] = Field(None, description="Notes to add")
    final_response: Optional[str] = Field(None, description="Final response to send to user")


class ReviewResponse(BaseModel):
    id: str
    feedback_text: str
    product: str
    nps_score: int
    categories: List[str]
    assigned_team: str
    status: str
    user_id: str
    created_at: str
    is_technical: bool
    duplicate_note: Optional[str] = ""
    intent_note: Optional[str] = ""
    original_response: str
    notes: Optional[str] = ""
    final_response: Optional[str] = ""


@router.get("/reviews", response_model=List[ReviewResponse])
async def get_reviews(team: Optional[str] = None, category: Optional[str] = None):
    if team:
        reviews = review_service.get_all_reviews(team_filter=team)
    else:
        reviews = review_service.get_pending_reviews(category_filter=category)
    return reviews


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str):
    review = review_service.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.put("/reviews/{review_id}")
async def update_review(review_id: str, request: ReviewUpdateRequest):
    success = review_service.update_review(
        review_id,
        action=request.action,
        notes=request.notes,
        final_response=request.final_response
    )
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"success": True, "message": f"Review updated: {request.action}"}


@router.get("/teams")
async def get_teams():
    return routing_service.get_all_teams()


@router.get("/user-ids")
async def get_user_ids():
    return vector_store.get_all_user_ids()


@router.get("/stats")
async def get_stats():
    feedbacks = vector_store.get_all_feedbacks()
    reviews = review_service.get_pending_reviews()

    ai_responses = len(feedbacks)
    human_followups = sum(1 for r in reviews if r.get("final_response"))
    resolved = sum(1 for r in reviews if r.get("status") == "resolved")

    return {
        "total": ai_responses,
        "ai_responses": ai_responses,
        "human_followups": human_followups,
        "resolved": resolved
    }


class PreviewFeedback(BaseModel):
    id: str
    user_id: str
    feedback_text: str
    product: str
    nps_score: int
    categories: List[str]
    ai_response: str
    human_response: Optional[str] = None
    status: str
    created_at: str
    kb_references: Optional[List[str]] = None


class PreviewResponse(BaseModel):
    feedbacks: List[PreviewFeedback]
    stats: dict


@router.get("/preview-user", response_model=PreviewResponse)
async def get_preview_user(user_id: Optional[str] = None):
    feedbacks = vector_store.get_all_feedbacks()
    pending_reviews = review_service.get_pending_reviews()
    all_reviews = review_service.get_all_reviews()
    resolved_reviews = [r for r in all_reviews if r.get("status") == "resolved"]

    reviewed_feedback_ids = set()
    for review in pending_reviews + resolved_reviews:
        fid = review.get("feedback_id", "")
        if fid:
            reviewed_feedback_ids.add(fid)

    feedback_map = {}
    for fb in feedbacks:
        fid = fb.get("id") or fb.get("metadata", {}).get("feedback_id", "")
        feedback_map[fid] = {
            "id": fid,
            "feedback_text": fb.get("text", ""),
            "product": fb.get("metadata", {}).get("product", "Unknown"),
            "nps_score": fb.get("metadata", {}).get("nps_score", 0),
            "user_id": fb.get("metadata", {}).get("user_id", "anonymous"),
            "categories": fb.get("metadata", {}).get("categories") or [],
            "ai_response": fb.get("metadata", {}).get("llm_response", ""),
            "kb_references": fb.get("metadata", {}).get("kb_references") or [],
            "created_at": fb.get("metadata", {}).get("timestamp", ""),
            "human_response": None,
            "status": "completed"
        }
        if fid in reviewed_feedback_ids:
            feedback_map[fid]["status"] = "pending"

    for review in pending_reviews + resolved_reviews:
        fid = review.get("feedback_id", "")
        if fid in feedback_map:
            feedback_map[fid]["status"] = review.get("status", "pending")
            if review.get("final_response"):
                feedback_map[fid]["human_response"] = review.get("final_response")

    result_list = list(feedback_map.values())
    result_list.sort(key=lambda x: x["created_at"], reverse=True)

    if user_id:
        result_list = [f for f in result_list if f["user_id"] == user_id]

    ai_count = len(result_list)
    human_count = sum(1 for f in result_list if f["human_response"])
    resolved_count = sum(1 for f in result_list if f["status"] == "resolved")

    return {
        "feedbacks": result_list,
        "stats": {
            "total": ai_count,
            "ai_responses": ai_count,
            "human_followups": human_count,
            "resolved": resolved_count
        }
    }