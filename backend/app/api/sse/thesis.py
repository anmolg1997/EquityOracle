"""SSE endpoint for streaming thesis generation."""

from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import StreamingResponse

router = APIRouter(prefix="/sse", tags=["sse"])


@router.get("/thesis/{ticker}")
async def stream_thesis(ticker: str):
    """SSE stream of AI-generated investment thesis."""

    async def event_stream():
        yield f"data: {{\"type\": \"start\", \"ticker\": \"{ticker}\"}}\n\n"
        yield f"data: {{\"type\": \"thesis\", \"content\": \"Investment thesis for {ticker} — configure LLM in settings\"}}\n\n"
        yield f"data: {{\"type\": \"done\"}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
