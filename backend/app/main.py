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
    version="v2026.4.20.1", 
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

@app.middleware("http")
async def disable_caching_middleware(request, call_next):
    # Strip conditional headers so Starlette/FastAPI doesn't return 304
    # Create a new scope with modified headers
    headers = dict(request.headers)
    headers.pop("if-none-match", None)
    headers.pop("if-modified-since", None)
    
    # We can't easily mutate the request object headers in FastAPI/Starlette mid-flight,
    # but we can ensure the response always has no-cache headers and NO ETAG.
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    # Remove ETag to stop the browser from even trying to use If-None-Match
    if "ETag" in response.headers:
        del response.headers["ETag"]
    if "etag" in response.headers:
        del response.headers["etag"]
        
    return response

app.include_router(stats.router)
app.include_router(matches.router)
app.include_router(players.router)
app.include_router(balancer.router)
app.include_router(admin.router)
app.include_router(server.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
