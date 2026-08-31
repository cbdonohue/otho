from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.events import Event

router = APIRouter(tags=["live"])


class ConnectionHub:
    def __init__(self) -> None:
        self._rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, league_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._rooms.setdefault(league_id, []).append(ws)

    def disconnect(self, league_id: str, ws: WebSocket) -> None:
        peers = self._rooms.get(league_id, [])
        if ws in peers:
            peers.remove(ws)

    async def broadcast(self, event: Event) -> None:
        if not event.league_id:
            targets = [ws for room in self._rooms.values() for ws in room]
        else:
            targets = list(self._rooms.get(event.league_id, []))
        dead: list[WebSocket] = []
        payload = {
            "type": event.type,
            "league_id": event.league_id,
            "payload": event.payload,
            "occurred_at": event.occurred_at.isoformat(),
        }
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            for lid, room in self._rooms.items():
                if ws in room:
                    room.remove(ws)


hub = ConnectionHub()


@router.websocket("/api/live/{league_id}")
async def live(websocket: WebSocket, league_id: str):
    await hub.connect(league_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(league_id, websocket)
