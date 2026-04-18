from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, SessionLocal
from app.routers import matches, players, stats, balancer, admin, server
from app.routers.admin import run_consolidation


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # Automatically merge any alias player records into their master on every startup.
    # This is idempotent — if the DB is already clean it does nothing.
    db = SessionLocal()
    try:
        result = run_consolidation(db)
        print(f"[Startup] Alias consolidation: {result.get('message')}")
    except Exception as e:
        print(f"[Startup] Alias consolidation warning: {e}")
    finally:
        db.close()
    yield


app = FastAPI(
    title="ET:Legacy Stats Server", 
    version="v2026.4.11.1", 
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
