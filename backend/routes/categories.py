"""Category routes for opportunity filtering"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["categories"])


@router.get("/categories")
async def get_all_categories():
    """Get all available opportunity categories for filtering"""
    try:
        from category_service import get_category_service
        category_service = get_category_service()
        categories = category_service.get_categories_for_display()
        return {
            "status": "success",
            "categories": categories,
            "count": len(categories)
        }
    except Exception as e:
        print(f"[CATEGORIES] Error loading categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load categories: {str(e)}")


@router.get("/categories/{category_id}")
async def get_category_detail(category_id: int):
    """Get detailed information about a specific category including keywords and prompts"""
    try:
        from category_service import get_category_service
        category_service = get_category_service()

        category = category_service.get_category_by_id(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        keywords = category_service.get_category_keywords(category_id)
        prompt = category_service.get_category_search_prompt(category_id)

        return {
            "status": "success",
            "category": category,
            "keywords": keywords,
            "search_prompt": prompt
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CATEGORIES] Error loading category {category_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load category: {str(e)}")
