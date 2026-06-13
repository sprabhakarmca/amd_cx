from fastapi import APIRouter, HTTPException
from app.services.knowledge_base import knowledge_base
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["knowledge"])

class KBItem(BaseModel):
    title: str
    content: str
    tags: List[str]

class KBResponse(BaseModel):
    id: int
    title: str
    content: str
    tags: List[str]
    relevance_score: Optional[float] = None


@router.get("/knowledge")
async def get_all_knowledge():
    return {"items": knowledge_base.get_all()}


@router.post("/knowledge")
async def add_knowledge(item: KBItem):
    result = knowledge_base.add(item.title, item.content, item.tags)
    return {"success": True, "item": result}


@router.delete("/knowledge/{kb_id}")
async def delete_knowledge(kb_id: int):
    success = knowledge_base.remove(kb_id)
    return {"success": success}


@router.get("/knowledge/search")
async def search_knowledge(q: str, top_k: int = 5):
    results = knowledge_base.search(q, top_k=top_k)
    return {"results": results}