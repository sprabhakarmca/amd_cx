from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FeedbackRequest(BaseModel):
    product: Optional[str] = Field(None, description="Product name (optional)")
    feedback_text: str = Field(..., description="User's feedback")
    nps_score: int = Field(..., ge=1, le=10, description="NPS score from 1 to 10")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class ClassificationItem(BaseModel):
    category: str
    subcategory: str = ""
    confidence: float = 0.0
    is_primary: bool = False


class FeedbackResponse(BaseModel):
    success: bool
    message: str
    llm_response: Optional[str] = None
    nps_score: int = Field(..., description="NPS score")
    categories: Optional[List[str]] = Field(default_factory=list, description="Auto-detected categories")
    classifications: Optional[List[ClassificationItem]] = None
    confidence: float = 0.0
    sentiment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    is_technical: Optional[bool] = False
    duplicate_note: Optional[str] = None
    intent_note: Optional[str] = None
    needs_review: Optional[bool] = False
    assigned_team: Optional[str] = None
    kb_references: Optional[List[str]] = None


class ChatRequest(BaseModel):
    message: str = Field(..., description="Product manager's question")
    product_filter: Optional[str] = Field(None, description="Filter by product name")
    min_nps: Optional[int] = Field(None, ge=1, le=10, description="Minimum NPS score filter")
    max_nps: Optional[int] = Field(None, ge=1, le=10, description="Maximum NPS score filter")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")


class ChatResponse(BaseModel):
    success: bool
    response: str
    relevant_feedbacks: Optional[list] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class CategoryListResponse(BaseModel):
    categories: List[str]
    few_shot_examples: List[dict]


class CategoryAddRequest(BaseModel):
    category: str = Field(..., description="New category to add")


class CategoryUpdateRequest(BaseModel):
    old_category: str = Field(..., description="Category to update")
    new_category: str = Field(..., description="New category name")


class CategoryDeleteRequest(BaseModel):
    category: str = Field(..., description="Category to delete")