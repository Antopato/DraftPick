from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..draft.engine import DraftError
from ..draft.sequence import Team
from ..services.ddragon import ChampionCatalogError
from ..services.room_manager import UnknownTokenError, manager

router = APIRouter()


@router.websocket("/ws/{token}")
async def draft_websocket(websocket: WebSocket, token: str) -> None:
    await websocket.accept()
    try:
        live, role = await manager.get_by_token(token)
    except UnknownTokenError:
        await websocket.close(code=4404, reason="Sala no encontrada.")
        return
    except ChampionCatalogError as exc:
        await websocket.close(code=4503, reason=str(exc))
        return

    await manager.register(live, websocket, role)
    try:
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                continue
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if role == "spectator":
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "El espectador no puede realizar acciones.",
                    }
                )
                continue
            try:
                await manager.handle(live, Team(role), message)
            except DraftError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.unregister(live, websocket)
