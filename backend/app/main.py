from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import matches, players, stats, balancer, admin, server


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ET:Legacy Stats Server", 
    version="2026.4.4.3", 
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stats.router)
app.include_router(matches.router)
app.include_router(players.router)
app.include_router(balancer.router)
app.include_router(admin.router)
app.include_router(server.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
