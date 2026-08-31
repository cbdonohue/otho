from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "product": "otho"}


@router.get("/api/health")
async def api_health():
    return {"status": "ok", "product": "otho"}
