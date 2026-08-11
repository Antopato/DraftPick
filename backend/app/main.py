from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import create_tables
from .routers import analysis, rooms, ws
from .services.ddragon import ChampionCatalogError, catalog


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    try:
        await catalog.get_pool()  # warm the champion cache (best effort)
    except ChampionCatalogError:
        pass
    yield


app = FastAPI(title="DraftPick API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms.router)
app.include_router(ws.router)
app.include_router(analysis.router)
