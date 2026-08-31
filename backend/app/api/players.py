from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.services.player_service import PlayerService

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("/search")
async def search_players(q: str, limit: int = 20, session: AsyncSession = Depends(get_session)):
    players = await PlayerService(session).search(q, limit=limit)
    return {"players": [p.model_dump() for p in players]}


@router.get("/trending")
async def trending(kind: str = "add", session: AsyncSession = Depends(get_session)):
    items = await PlayerService(session).trending(kind)
    return {"trending": [t.model_dump() for t in items]}


@router.get("/{player_id}")
async def get_player(player_id: str, session: AsyncSession = Depends(get_session)):
    player = await PlayerService(session).get_player(player_id)
    if not player:
        raise HTTPException(404, "player not found")
    return {"player": player.model_dump()}
