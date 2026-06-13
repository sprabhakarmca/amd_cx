from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import CategoryListResponse, CategoryAddRequest, CategoryUpdateRequest, CategoryDeleteRequest
from app.services.category_service import category_service

router = APIRouter(prefix="/api", tags=["categories"])


@router.get("/categories")
async def get_categories(hierarchical: bool = Query(False, description="Return hierarchical taxonomy")):
    try:
        data = category_service.get_all()
        if hierarchical:
            return {
                "categories": data["categories"],
                "total_buckets": category_service.get_category_count(),
                "few_shot_examples": data["few_shot_examples"]
            }
        flat_names = category_service.get_category_names()
        return CategoryListResponse(
            categories=flat_names,
            few_shot_examples=data["few_shot_examples"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categories")
async def add_category(request: CategoryAddRequest):
    try:
        success = category_service.add_category(request.category)
        if success:
            return {"success": True, "message": f"Category '{request.category}' added successfully"}
        else:
            return {"success": False, "message": f"Category '{request.category}' already exists"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/categories")
async def update_category(request: CategoryUpdateRequest):
    try:
        success = category_service.update_category(request.old_category, request.new_category)
        if success:
            return {"success": True, "message": f"Category updated from '{request.old_category}' to '{request.new_category}'"}
        else:
            return {"success": False, "message": f"Category '{request.old_category}' not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/categories")
async def delete_category(request: CategoryDeleteRequest):
    try:
        success = category_service.delete_category(request.category)
        if success:
            return {"success": True, "message": f"Category '{request.category}' deleted successfully"}
        else:
            return {"success": False, "message": f"Category '{request.category}' not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))