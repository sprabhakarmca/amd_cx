from fastapi import APIRouter
from app.models.schemas import FeedbackRequest, FeedbackResponse
from app.graph.workflow import run_feedback_workflow
from datetime import datetime
import traceback

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    try:
        result = run_feedback_workflow(
            product=request.product,
            feedback_text=request.feedback_text,
            nps_score=request.nps_score,
            user_id=request.user_id
        )

        if result.get("error"):
            return FeedbackResponse(
                success=False,
                message=result["error"],
                llm_response=None,
                nps_score=request.nps_score,
                categories=[],
                timestamp=datetime.now()
            )

        classifications_raw = result.get("classifications") or []
        classification_items = []
        for c in classifications_raw:
            if isinstance(c, dict):
                classification_items.append({
                    "category": c.get("category", ""),
                    "subcategory": c.get("subcategory", ""),
                    "confidence": c.get("confidence", 0.0),
                    "is_primary": c.get("is_primary", False)
                })

        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully",
            llm_response=result.get("llm_response"),
            nps_score=request.nps_score,
            categories=result.get("categories", []),
            classifications=classification_items,
            confidence=result.get("confidence", 0.0),
            sentiment=result.get("sentiment"),
            timestamp=datetime.now(),
            is_technical=result.get("is_technical", False),
            duplicate_note=result.get("duplicate_note"),
            intent_note=result.get("intent_note"),
            needs_review=result.get("needs_review", False),
            assigned_team=result.get("assigned_team"),
            kb_references=result.get("kb_references")
        )

    except Exception as e:
        traceback.print_exc()
        return FeedbackResponse(
            success=False,
            message=f"Workflow error: {str(e)}",
            llm_response=None,
            nps_score=request.nps_score,
            categories=[],
            timestamp=datetime.now()
        )