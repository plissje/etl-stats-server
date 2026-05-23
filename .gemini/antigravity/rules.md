# 🖥️ Coding Rules & Standards — etl-stats-server

A full-stack stats & skill-rating platform for competitive ET: Legacy gathers. Tracks match data, computes SR via OpenSkill (PlackettLuce), and powers a team balancer for fair matchups.

> See **workflow.md** for dev process, deployment, and hygiene rules.
> See **et_rules.md** for ET game mechanics, role classifications, and balancer logic.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI ≥ 0.115, Python 3.12+ |
| **ORM** | SQLAlchemy 2.x (Mapped / mapped_column style) |
| **Database** | SQLite (dev) — engine configured via `DATABASE_URL` env var |
| **Validation & Serialization** | Pydantic v2 (`BaseModel`, `ConfigDict`) |
| **Rating Engine** | openskill (PlackettLuce) |
| **Frontend** | Vite + React 19 + TypeScript 5, Tailwind CSS v4 |
| **Charts** | Recharts |
| **Routing** | react-router-dom v7 |
| **Tests** | pytest + httpx (backend) |

---

## General Principles

1. **No overengineering**: Add complexity only when the problem explicitly requires it.
2. **Explicit over implicit**: Name variables, functions, and models clearly; avoid single-letter variables except in tight, localized loops.
3. **One responsibility per file**: Parsers parse, services orchestrate, routers route, models define structures.
4. **Strict typing**: Use Python type annotations everywhere. Use strong TypeScript types in `api.ts` — never use `any` unless parsing highly unstructured, untrusted external payloads.
5. **No silent failures**: Avoid bare `except: pass`. Log or re-raise exceptions with detailed, structured context.

---

## Backend Rules (Python / FastAPI)

### Project Structure
```
backend/app/
  models.py        ← SQLAlchemy ORM models only (no business logic)
  schemas.py       ← Pydantic request / response models only
  database.py      ← Engine, session, init_db() — no business logic
  config.py        ← Settings via pydantic-settings, read from .env
  deps.py          ← FastAPI dependency functions (get_db etc.)
  rating.py        ← Rating algorithm (pure functions, no DB access)
  parsers/         ← Pure parsing functions: events, weapon_stats, names
  services/        ← Orchestration: DB writes, calling parsers & rating
  routers/         ← FastAPI routers — thin, delegate to services
  main.py          ← App factory: include routers, init_db on startup
```

### Models (`models.py`)
- Use SQLAlchemy 2.x `Mapped[T]` / `mapped_column()` — **never** old `Column()` style.
- Declare relationships explicitly with `Mapped[list["..."]]` / `Mapped["..." | None]`.
- `created_at` / `updated_at` must default to `datetime.utcnow` (do not use `timezone.utc` until a migration strategy is in place).
- Add `index=True` on all Foreign Key columns and any frequently-filtered or sorted fields.
- Use `UniqueConstraint` via `__table_args__` for composite unique keys.
- Store arbitrary JSON blobs as `Text` with a `_json` suffix (e.g., `nemesis_json`).

### Schemas (`schemas.py`)
- Separate **input** schemas (e.g., `SubmitStatsBody`) from **output** schemas (e.g., `MatchDetailOut`).
- Output schemas must use `model_config = ConfigDict(from_attributes=True)` when deserializing ORM objects.
- Only add `extra="allow"` on inbound schemas where the external payload is highly dynamic.
- Replace `list[dict[str, Any]]` fields with typed Pydantic models whenever the JSON schema is known.

### Routers (`routers/`)
- Declare explicit `response_model=` on every endpoint.
- Routers must not contain business logic — delegate immediately to `services/`.
- Use Python 3.10+ union syntax (`T | None`) instead of `Optional[T]`.

### Services (`services/`)
- `ingest.py` owns the full match ingestion transaction — calls parsers, computes rating changes, and commits.
- All database writes must go through service functions; routers must never call `db.add()` or `db.delete()` directly.
- Use `db.flush()` mid-function to generate primary keys; call `db.commit()` exactly once at the end of the transaction.
- When re-ingesting an existing match: roll back rating history deltas **before** deleting rows.

### Parsers (`parsers/`)
- Must be **pure functions** — no database access, no network calls, no side effects.
- Normalize GUIDs consistently: always `.strip().upper()` — use the `_norm_guid()` pattern.
- Use `@dataclass` for structured intermediate results (e.g., `EventMetrics`, `UnpackedWeaponStats`).

### Rating (`rating.py`)
- Must be a pure module — no database imports, no SQLAlchemy.
- The XP modifier cap of `0.5x–1.5x` is intentional; do not remove it.
- `compute_display_rating(mu, sigma)` is the canonical display formula — always use it.

### Testing
- All backend tests live in `backend/tests/`.
- Use `conftest.py` for fixtures (in-memory SQLite sessions, test client).
- Name tests `test_<module>_<behaviour>` (e.g., `test_rating_draw_result`).
- **Run tests**: `PYTHONPATH=. .venv/bin/pytest tests/` from the `backend/` directory.

---

## Frontend Rules (TypeScript / React / Tailwind)

### Project Structure
```
frontend/src/
  api.ts           ← All fetch calls + exported TypeScript types
  App.tsx          ← Router, Layout component, main layout container
  main.tsx         ← App entry point and mounting
  index.css        ← Global Tailwind CSS directives & theme configurations
  components/      ← Shared UI elements (badges, navigation, stat grids, etc.)
  pages/           ← One file per page (Dashboard.tsx, MatchDetail.tsx, etc.)
  util/            ← Pure helper functions (no React dependencies)
  assets/          ← Static files and images
```

### `api.ts` — The Single API Layer
- **All** `fetch()` calls live in `api.ts` — never perform inline fetches inside components.
- Every API function must be `async` and throw on non-ok responses.
- Type every response with an exported `type` — never use `any` for known shapes.
- Encode all URL parameters using `encodeURIComponent()`.

### Components & Pages
- One page = one file in `pages/`. Pages should not grow past ~400 lines.
- Avoid passing raw API types into deep component trees; destructure or map props at the page level.
- Use `useState` + `useEffect` for data fetching; extract into a custom hook if used in more than one component.

### Styling (Tailwind v4)
- The project uses **Tailwind CSS v4** (configured via `@tailwindcss/vite`).
- The design palette is dark/zinc-based with violet/fuchsia accents — keep consistent.
- Do **not** use inline `style={{}}` for layout; prefer Tailwind classes.
- Responsive breakpoints: prefer `md:` for tablet/desktop pivots.
- Animation: use `transition-all duration-300` consistently for interactive elements.

### TypeScript
- `strict` mode is on — keep it that way.
- Prefer `type` over `interface` for data shapes.
- Do not suppress type errors with `// @ts-ignore` — fix the types.

---

## Environment & Secrets

- All configuration lives in `backend/.env` (gitignored). See `.env.example` for keys.
- Access env vars only via `app.config.settings` (pydantic-settings); never `os.environ` directly.
- `store_raw`: set to `False` in production to avoid storing full payloads.

---

## Git & Commit Conventions

- Use imperative present tense: `Add`, `Fix`, `Remove`, `Refactor`.
- Keep changes atomic: one logical change per commit.
- Do not commit `.env`, `*.db`, `__pycache__`, `.venv`, `node_modules`, `dist`.

---

## Things to Never Do

- **Never deploy automatically** without presenting changes and waiting for manual user verification.
- **Never create scratch scripts** in the repo root or `backend/` / `frontend/` — use `scratch/`.
- **Never mix Rifle Engineers and SMG Engineers** in balancer logic — they must be balanced separately.
- Do not add `datetime.timezone.utc` without a migration plan for existing rows.
- Do not bypass `ingest_match_payload` for inserting match data — it owns the rating rollback logic.
- Do not add `@router.get` endpoints with raw SQL strings — use the SQLAlchemy query API.
- Do not import `models` in `parsers` or `rating` — those layers must stay pure.
- Do not introduce a new charting library without discussion; Recharts is the established choice.
- Do not hardcode team numbers as literal strings — team `1` = Axis, team `2` = Allies; always use constants or compare to the integer.

---

## Deployment & Live Environment (Unraid)

- **Production Host**: Runs on Unraid (`unraid.local.maryan.io` / `10.0.0.200`), managed via **Dockge**.
- **Deployment**: Run `./deploy_unraid.sh` from the PC (manually, after user approval).
- **Dockge Web UI**: `http://10.0.0.200:5001`
- **Live Logs**: `ssh root@unraid "docker logs -f etl-stats-server"`
- **Interactive Terminal**: `ssh root@unraid "docker exec -it etl-stats-server sh"`
