"""SSE endpoint for streaming Bull/Bear debate."""

from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import StreamingResponse

router = APIRouter(prefix="/sse", tags=["sse"])


@router.get("/debate/{ticker}")
async def stream_debate(ticker: str):
    """SSE stream of the debate analysis for a given ticker."""

    async def event_stream():
        yield f"data: {{\"type\": \"start\", \"ticker\": \"{ticker}\"}}\n\n"
        yield f"data: {{\"type\": \"bull\", \"content\": \"Bull case analysis for {ticker}...\"}}\n\n"
        yield f"data: {{\"type\": \"bear\", \"content\": \"Bear case analysis for {ticker}...\"}}\n\n"
        yield f"data: {{\"type\": \"synthesis\", \"content\": \"Synthesis — requires LLM configuration\"}}\n\n"
        yield f"data: {{\"type\": \"done\"}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
