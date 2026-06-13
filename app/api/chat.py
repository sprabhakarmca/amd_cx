from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.graph.workflow import run_chat_workflow
from datetime import datetime

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_feedbacks(request: ChatRequest):
    try:
        result = run_chat_workflow(
            message=request.message,
            product_filter=request.product_filter,
            min_nps=request.min_nps,
            max_nps=request.max_nps,
            categories_filter=request.categories
        )

        if result.get("error"):
            return ChatResponse(
                success=False,
                response=result["error"],
                relevant_feedbacks=None,
                timestamp=datetime.now()
            )

        relevant_feedbacks = result.get("relevant_feedbacks", [])
        formatted_feedbacks = [
            {
                "text": fb.get("text"),
                "product": fb.get("metadata", {}).get("product"),
                "nps_score": fb.get("metadata", {}).get("nps_score"),
                "categories": fb.get("metadata", {}).get("categories", []),
                "user_id": fb.get("metadata", {}).get("user_id"),
                "timestamp": fb.get("metadata", {}).get("timestamp")
            }
            for fb in relevant_feedbacks
        ]

        return ChatResponse(
            success=True,
            response=result.get("llm_response", "No response generated"),
            relevant_feedbacks=formatted_feedbacks,
            timestamp=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))