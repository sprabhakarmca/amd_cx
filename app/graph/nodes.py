from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from app.services.routing_service import routing_service
from app.services.review_service import review_service
from app.services.knowledge_base import knowledge_base


class FeedbackState(TypedDict):
    product: Optional[str]
    feedback_text: str
    nps_score: int
    user_id: Optional[str]
    feedback_id: Optional[str]
    categories: List[str]
    classifications: Optional[List[Dict[str, Any]]]
    confidence: float
    sentiment: Optional[str]
    llm_response: Optional[str]
    error: Optional[str]
    is_technical: bool
    duplicate_note: Optional[str]
    intent_note: Optional[str]
    needs_review: bool
    assigned_team: Optional[str]
    suggested_team: Optional[str]
    kb_references: Optional[List[str]]


class ChatState(TypedDict):
    message: str
    product_filter: Optional[str]
    min_nps: Optional[int]
    max_nps: Optional[int]
    categories_filter: Optional[List[str]]
    relevant_feedbacks: Optional[List]
    llm_response: Optional[str]
    error: Optional[str]


def check_duplicates_node(state: FeedbackState) -> FeedbackState:
    if state.get("error"):
        return state
    
    state["duplicate_note"] = None
    try:
        user_id = state.get("user_id")
        if user_id and user_id != "anonymous":
            similar = vector_store.query(
                query_text=state["feedback_text"],
                product_filter=state.get("product"),
                n_results=3,
                min_nps=None,
                max_nps=None,
                categories=None
            )
            if similar:
                for fb in similar:
                    fb_user = fb.get("metadata", {}).get("user_id", "anonymous")
                    if fb_user == user_id:
                        state["duplicate_note"] = "Similar feedback found from this user. Consider adding to existing feedback."
                        break
    except Exception:
        pass
    return state


def check_technical_node(state: FeedbackState) -> FeedbackState:
    if state.get("error"):
        return state
    
    state["is_technical"] = routing_service.is_technical(state["feedback_text"])
    return state


def store_feedback_node(state: FeedbackState) -> FeedbackState:
    if state.get("error"):
        return state
    
    try:
        feedback_id = vector_store.add_feedback(
            feedback_text=state["feedback_text"],
            product=state.get("product", "Unknown"),
            nps_score=state["nps_score"],
            user_id=state.get("user_id"),
            categories=state.get("categories", [])
        )
        state["feedback_id"] = feedback_id
        vector_store.store_embedding(
            feedback_id=feedback_id,
            feedback_text=state["feedback_text"],
            product=state.get("product", "Unknown"),
            categories=state.get("categories", []),
            nps_score=state["nps_score"],
            user_id=state.get("user_id", "anonymous"),
            created_at=datetime.now().isoformat()
        )
    except Exception as e:
        state["error"] = f"Failed to store feedback: {str(e)}"
    return state


def update_feedback_response_node(state: FeedbackState) -> FeedbackState:
    if state.get("error"):
        return state
    
    try:
        if state.get("feedback_id") and state.get("llm_response"):
            vector_store.update_feedback_response(
                feedback_id=state["feedback_id"],
                llm_response=state["llm_response"],
                kb_references=state.get("kb_references")
            )
            vector_store.update_embedding_categories(
                feedback_id=state["feedback_id"],
                categories=state.get("categories", [])
            )
    except Exception as e:
        pass
    return state


def categorize_and_respond_node(state: FeedbackState) -> FeedbackState:
    if state.get("error"):
        return state

    try:
        if state.get("is_technical"):
            state["llm_response"] = routing_service.get_technical_response()
            state["kb_references"] = []
            state["categories"] = []
            state["classifications"] = []
            state["confidence"] = 0.0
            state["sentiment"] = "negative"
            state["needs_review"] = True
            state["suggested_team"] = "General Support"
        else:
            kb_results = knowledge_base.search(state["feedback_text"], top_k=5)
            kb_context = ""
            if kb_results:
                kb_parts = []
                for item in kb_results:
                    kb_parts.append(f"- {item['title']}: {item['content']}")
                kb_context = "\n".join(kb_parts)

            categories, response_text, kb_titles_used, needs_review, suggested_team, classifications, confidence = llm_service.categorize_and_respond(
                feedback_text=state["feedback_text"],
                product=state.get("product", "Unknown"),
                kb_context=kb_context,
                kb_results=kb_results
            )

            state["categories"] = categories if categories else []
            state["classifications"] = classifications
            state["confidence"] = confidence
            state["sentiment"] = classifications[0].get("sentiment", "neutral") if classifications else "neutral"
            state["llm_response"] = response_text
            state["kb_references"] = kb_titles_used
            state["needs_review"] = needs_review
            state["suggested_team"] = suggested_team

    except Exception as e:
        state["error"] = f"Failed to process feedback: {str(e)}"
    return state


def route_to_team_node(state: FeedbackState) -> FeedbackState:
    if state.get("error"):
        return state

    if state.get("needs_review"):
        suggested_team = state.get("suggested_team", "none")
        if suggested_team and suggested_team != "none":
            state["assigned_team"] = suggested_team
        else:
            categories = state.get("categories", [])
            top_cat = categories[0] if categories else None
            if top_cat:
                team = routing_service.get_team_for_category(top_cat)
                state["assigned_team"] = team['name'] if team else "General Support"
            else:
                state["assigned_team"] = "General Support"
    else:
        state["assigned_team"] = "none"

    return state


def generate_feedback_response_node(state: FeedbackState) -> FeedbackState:
    return state


def create_review_node(state: FeedbackState) -> FeedbackState:
    if state.get("error"):
        return state

    if not state.get("needs_review", False):
        return state

    try:
        assigned_team = state.get("assigned_team", "Unassigned")
        if assigned_team == "none":
            return state

        review_service.create_review(
            feedback_id=state.get("feedback_id", ""),
            feedback_text=state["feedback_text"],
            product=state["product"],
            nps_score=state["nps_score"],
            categories=state.get("categories", []),
            assigned_team=assigned_team,
            original_response=state.get("llm_response", ""),
            user_id=state.get("user_id"),
            is_technical=state.get("is_technical", False),
            duplicate_note=state.get("duplicate_note"),
            intent_note=state.get("intent_note")
        )
    except Exception as e:
        state["error"] = f"Failed to create review: {str(e)}"
    return state


def retrieve_feedbacks_node(state: ChatState) -> ChatState:
    try:
        relevant_feedbacks = vector_store.search_similar(
            query_text=state["message"],
            product_filter=state.get("product_filter"),
            n_results=10,
            min_nps=state.get("min_nps"),
            max_nps=state.get("max_nps"),
            categories=state.get("categories_filter")
        )
        state["relevant_feedbacks"] = relevant_feedbacks
    except Exception as e:
        state["error"] = f"Failed to retrieve feedbacks: {str(e)}"
    return state


def generate_chat_response_node(state: ChatState) -> ChatState:
    if state.get("error"):
        return state

    try:
        llm_response = llm_service.generate_chat_response(
            user_message=state["message"],
            relevant_feedbacks=state.get("relevant_feedbacks", []),
            product_filter=state.get("product_filter")
        )
        state["llm_response"] = llm_response
    except Exception as e:
        state["error"] = f"Failed to generate chat response: {str(e)}"
    return state