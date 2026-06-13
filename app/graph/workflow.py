from langgraph.graph import StateGraph, END
from typing import Optional
from app.graph.nodes import (
    FeedbackState,
    ChatState,
    check_duplicates_node,
    check_technical_node,
    store_feedback_node,
    categorize_and_respond_node,
    update_feedback_response_node,
    route_to_team_node,
    create_review_node,
    retrieve_feedbacks_node,
    generate_chat_response_node
)


def create_feedback_graph():
    workflow = StateGraph(FeedbackState)

    workflow.add_node("check_duplicates", check_duplicates_node)
    workflow.add_node("check_technical", check_technical_node)
    workflow.add_node("store_feedback", store_feedback_node)
    workflow.add_node("categorize_and_respond", categorize_and_respond_node)
    workflow.add_node("update_feedback_response", update_feedback_response_node)
    workflow.add_node("route_to_team", route_to_team_node)
    workflow.add_node("create_review", create_review_node)

    workflow.set_entry_point("check_duplicates")
    workflow.add_edge("check_duplicates", "check_technical")
    workflow.add_edge("check_technical", "store_feedback")
    workflow.add_edge("store_feedback", "categorize_and_respond")
    workflow.add_edge("categorize_and_respond", "update_feedback_response")
    workflow.add_edge("update_feedback_response", "route_to_team")
    workflow.add_edge("route_to_team", "create_review")
    workflow.add_edge("create_review", END)

    return workflow.compile()


def create_chat_graph():
    workflow = StateGraph(ChatState)

    workflow.add_node("retrieve_feedbacks", retrieve_feedbacks_node)
    workflow.add_node("generate_chat_response", generate_chat_response_node)

    workflow.set_entry_point("retrieve_feedbacks")
    workflow.add_edge("retrieve_feedbacks", "generate_chat_response")
    workflow.add_edge("generate_chat_response", END)

    return workflow.compile()


feedback_graph = create_feedback_graph()
chat_graph = create_chat_graph()


def run_feedback_workflow(
    product: Optional[str],
    feedback_text: str,
    nps_score: int,
    user_id: str = None
) -> dict:
    initial_state: FeedbackState = {
        "product": product or "Unknown",
        "feedback_text": feedback_text,
        "nps_score": nps_score,
        "user_id": user_id,
        "feedback_id": None,
        "categories": [],
        "classifications": None,
        "confidence": 0.0,
        "sentiment": None,
        "llm_response": None,
        "error": None,
        "is_technical": False,
        "duplicate_note": None,
        "intent_note": None,
        "needs_review": False,
        "assigned_team": None,
        "suggested_team": None,
        "kb_references": None
    }

    result = feedback_graph.invoke(initial_state)
    return result


def run_chat_workflow(
    message: str,
    product_filter: str = None,
    min_nps: int = None,
    max_nps: int = None,
    categories_filter: list = None
) -> dict:
    initial_state: ChatState = {
        "message": message,
        "product_filter": product_filter,
        "min_nps": min_nps,
        "max_nps": max_nps,
        "categories_filter": categories_filter,
        "relevant_feedbacks": None,
        "llm_response": None,
        "error": None
    }

    result = chat_graph.invoke(initial_state)
    return result