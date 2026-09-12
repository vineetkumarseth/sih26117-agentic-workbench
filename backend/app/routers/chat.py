from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_workbench
from app.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.guardrails import guard
from app.models.schemas import ChatRequest, ChatResponse, CitationOut, TraceStep
from app.security.audit import log_event
from app.security.auth import get_current_user
from app.security.rate_limit import limiter

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


@router.post("", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def chat(
    request: Request,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else None

    # 1. Guardrail check on the INPUT before it ever reaches an agent or the LLM.
    input_check = await guard.check_input_full(payload.message)
    if not input_check.allowed:
        await log_event(
            db,
            event_type="guardrail_block",
            user_id=current_user.id,
            username=current_user.username,
            route="input",
            input_text=payload.message,
            detail=input_check.reason,
            allowed=False,
            client_ip=client_ip,
        )
        return ChatResponse(
            answer="That request was blocked by the workbench's input guardrails.",
            route=[],
            trace=[],
            blocked=True,
            block_reason=input_check.reason,
        )

    # 2. Run the multi-agent graph.
    result = await run_workbench(
        session_id=payload.session_id,
        owner_id=current_user.id,
        query=payload.message,
        image_base64=payload.image_base64,
    )
    answer = result["answer"] or ""

    # 3. Guardrail check on the OUTPUT before it goes back to the user.
    output_check = guard.check_output(answer)
    if not output_check.allowed:
        await log_event(
            db,
            event_type="guardrail_block",
            user_id=current_user.id,
            username=current_user.username,
            route="output",
            input_text=answer,
            detail=output_check.reason,
            allowed=False,
            client_ip=client_ip,
        )
        return ChatResponse(
            answer=output_check.redacted_text or "The response was withheld by the workbench's output guardrails.",
            route=result["route"],
            trace=[TraceStep(**step) for step in result["trace"]],
            blocked=True,
            block_reason=output_check.reason,
        )

    # 4. Audit + respond.
    await log_event(
        db,
        event_type="query",
        user_id=current_user.id,
        username=current_user.username,
        route=",".join(result["route"]),
        input_text=payload.message,
        detail=f"{len(result['trace'])} agent step(s)",
        allowed=True,
        client_ip=client_ip,
    )

    return ChatResponse(
        answer=answer,
        route=result["route"],
        trace=[TraceStep(**step) for step in result["trace"]],
        citations=[CitationOut(**c) for c in result["citations"]],
        blocked=False,
    )
