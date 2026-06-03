from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.llm import LLMClient
from backend.orchestrator import ChatOrchestrator
from backend.storage import Store


MAIN_HISTORY_ID = "main"
DEBUG_HISTORY_ID = "debug"


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


def get_store(settings: Settings = Depends(get_settings)) -> Store:
    return Store(settings.database_file)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = Store(settings.database_file)
    store.init()

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")

    @app.get("/debug")
    async def debug() -> FileResponse:
        return FileResponse(frontend_dir / "debug.html")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    def dump_history(store: Store, history_id: str, title: str) -> dict:
        store.ensure_history(history_id, title)
        return store.dump_history(history_id)

    async def respond_to_history(store: Store, history_id: str, title: str, content: str) -> dict:
        history = store.ensure_history(history_id, title)
        user_message = store.add_message(history_id, "user", content)
        messages = store.get_messages(history_id)

        orchestrator = ChatOrchestrator(LLMClient(get_settings()))
        result = await orchestrator.respond(messages, history["notes"], content)

        store.add_assessments(history_id, user_message["id"], result["assessments"])
        store.add_llm_calls(history_id, user_message["id"], result["calls"])
        store.update_notes(history_id, str(result["notes"]))
        assistant_message = store.add_message(history_id, "assistant", str(result["reply"]))

        return {
            "user_message": user_message,
            "assistant_message": assistant_message,
            "notes": result["notes"],
            "assessments": result["assessments"],
            "calls": result["calls"],
        }

    @app.get("/api/history")
    async def get_main_history(store: Store = Depends(get_store)) -> dict:
        return dump_history(store, MAIN_HISTORY_ID, "Main history")

    @app.post("/api/history/messages")
    async def add_main_message(payload: ChatRequest, store: Store = Depends(get_store)) -> dict:
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=422, detail="Message cannot be empty")
        return await respond_to_history(store, MAIN_HISTORY_ID, "Main history", content)

    @app.get("/api/debug/history")
    async def get_debug_history(store: Store = Depends(get_store)) -> dict:
        return dump_history(store, DEBUG_HISTORY_ID, "Debug history")

    @app.post("/api/debug/history/messages")
    async def add_debug_message(payload: ChatRequest, store: Store = Depends(get_store)) -> dict:
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=422, detail="Message cannot be empty")
        return await respond_to_history(store, DEBUG_HISTORY_ID, "Debug history", content)

    @app.post("/api/debug/history/simulate-user")
    async def simulate_debug_user(store: Store = Depends(get_store)) -> dict:
        history = store.ensure_history(DEBUG_HISTORY_ID, "Debug history")
        messages = store.get_messages(DEBUG_HISTORY_ID)
        orchestrator = ChatOrchestrator(LLMClient(get_settings()))
        content = (await orchestrator.simulate_user_response(messages, history["notes"])).strip()
        if not content:
            raise HTTPException(status_code=502, detail="Model returned an empty simulated response")
        return {"content": content}

    return app


app = create_app()
