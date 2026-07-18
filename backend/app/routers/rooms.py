from fastapi import APIRouter, HTTPException

from ..db import get_session
from ..models import Game, Room
from ..schemas import RoomCreate, RoomLinks
from ..services.ddragon import ChampionCatalogError
from ..services.lanes import lane_catalog
from ..services.room_manager import UnknownTokenError, manager

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/champion-lanes")
async def champion_lanes() -> dict:
    """Slim {championId: [lane,...]} map (from Meraki). Empty on upstream failure
    so the client's lane filter degrades gracefully instead of erroring."""
    return {"lanes": await lane_catalog.get_lanes()}


@router.post("/rooms", response_model=RoomLinks)
def create_room(payload: RoomCreate) -> RoomLinks:
    session = get_session()
    try:
        room = Room(
            mode=payload.mode,
            best_of=payload.best_of,
            timer_seconds=payload.timer_seconds,
            blue_name=payload.blue_name or "Equipo Azul",
            red_name=payload.red_name or "Equipo Rojo",
        )
        session.add(room)
        session.flush()
        session.add(Game(room_id=room.id, game_number=1))
        session.commit()
        return RoomLinks(
            room_id=room.id,
            blue_token=room.blue_token,
            red_token=room.red_token,
            spectator_token=room.spectator_token,
        )
    finally:
        session.close()


@router.get("/state/{token}")
async def get_state(token: str) -> dict:
    """Initial snapshot / one-off reconnection fallback (never main polling)."""
    try:
        live, role = await manager.get_by_token(token)
    except UnknownTokenError:
        raise HTTPException(status_code=404, detail="Sala no encontrada.")
    except ChampionCatalogError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    async with live.lock:
        return {**live.state_dict(), "your_role": role}
