"""Web API. The agent runs in a worker thread; its events are streamed to the browser
as Server-Sent Events (SSE): a long-lived HTTP response where each event is a
`data: {...}` line. The browser reads it with the built-in EventSource API.
"""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from committee.agent import AgentError
from committee.domain import InvestorProfile, load_candidates
from committee.events import Event
from committee.service import (
    CONFIG_DIR,
    ConfigError,
    DataSource,
    ProviderName,
    available_providers,
    run_analysis,
)
from committee.settings import BACKEND_DIR

WEB_DIR = BACKEND_DIR.parent / "web"

app = FastAPI(title="Investment Committee")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/config")
def config() -> dict[str, object]:
    return {
        "providers": available_providers(),
        "data_sources": list(DataSource),
        "profile": InvestorProfile.load(CONFIG_DIR / "profile.yaml"),
        "candidates": load_candidates(CONFIG_DIR / "candidates.yaml"),
    }


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


@app.get("/api/runs/stream")
async def stream_run(provider: ProviderName, data: DataSource) -> StreamingResponse:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

    def on_event(event: Event) -> None:
        # Called from the worker thread; hand the event to the event loop safely.
        loop.call_soon_threadsafe(queue.put_nowait, {"kind": "event", **event.model_dump()})

    def work() -> None:
        try:
            result = run_analysis(provider, data, on_event=on_event)
            message: dict[str, object] = {"kind": "result", "result": result.model_dump()}
        except (ConfigError, AgentError) as e:
            message = {"kind": "error", "message": str(e)}
        except Exception as e:  # surface unexpected failures in the UI rather than hanging
            message = {"kind": "error", "message": f"{type(e).__name__}: {e}"}
        loop.call_soon_threadsafe(queue.put_nowait, message)
        loop.call_soon_threadsafe(queue.put_nowait, None)

    async def events() -> AsyncIterator[str]:
        task = loop.run_in_executor(None, work)
        while (item := await queue.get()) is not None:
            yield _sse(item)
        await task

    return StreamingResponse(events(), media_type="text/event-stream")


# The plain HTML/CSS/JS frontend. Mounted last so /api/* routes take precedence.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
