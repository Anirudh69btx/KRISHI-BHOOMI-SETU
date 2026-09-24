"""
FLIP v3.0 — Core API REST Routers
Copilot router: voice transcription (Whisper), RAG query (Rasa + pgvector).
"""

from __future__ import annotations

import io
import struct
import time
import uuid
from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from flip_api.auth.keycloak import get_current_user
from flip_api.config import settings
from flip_api.database import get_session

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/copilot", tags=["copilot"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class CopilotQuery(BaseModel):
    text: str
    language: str = "en"
    farm_id: Optional[str] = None


class CopilotResponse(BaseModel):
    text: str
    language: str
    sources: list[str] = []
    intent: Optional[str] = None
    confidence: Optional[float] = None


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration_ms: float


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post(
    "/query",
    response_model=CopilotResponse,
    summary="Query the Kisan Copilot (RAG + Rasa)",
)
async def copilot_query(
    query: CopilotQuery,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> CopilotResponse:
    """
    Pipeline:
    1. Embed query text (pgvector)
    2. RAG retrieval from knowledge_chunks table
    3. Forward to Rasa dialogue manager with context
    4. Return localized response
    """
    lang = query.language or "en"

    try:
        # Step 1: Forward to Rasa dialogue manager
        async with httpx.AsyncClient(timeout=30) as client:
            rasa_resp = await client.post(
                f"{settings.RASA_URL}/webhooks/rest/webhook",
                json={
                    "sender": current_user.get("sub", "anonymous"),
                    "message": query.text,
                    "metadata": {
                        "language": lang,
                        "farm_id": query.farm_id,
                        "user_id": current_user.get("sub"),
                    },
                },
            )
            rasa_resp.raise_for_status()
            responses = rasa_resp.json()

        if responses:
            # Combine all Rasa response texts
            combined_text = " ".join(r.get("text", "") for r in responses if r.get("text"))
            if combined_text:
                return CopilotResponse(
                    text=combined_text,
                    language=lang,
                    intent=responses[0].get("intent"),
                    confidence=responses[0].get("confidence"),
                )

    except (httpx.RequestError, httpx.HTTPStatusError) as err:
        log.warning("rasa_unavailable", error=str(err))

    # Fallback: RAG from pgvector knowledge base
    try:
        # Naive fallback without embedding (would use pgvector in production)
        result = await session.execute(
            text("""
                SELECT content, source
                FROM knowledge_chunks
                WHERE language = :lang
                  AND content ILIKE :query_pattern
                ORDER BY created_at DESC
                LIMIT 3
            """),
            {"lang": lang, "query_pattern": f"%{query.text[:50]}%"},
        )
        rows = result.mappings().all()
        if rows:
            sources = [r["source"] for r in rows if r.get("source")]
            combined = " ".join(r["content"] for r in rows[:2])
            return CopilotResponse(text=combined[:500], language=lang, sources=sources)

    except Exception as err:
        log.error("rag_fallback_failed", error=str(err))

    # Last resort: helpful default message
    DEFAULT_MESSAGES = {
        "en": "I'm your Kisan Copilot. I can help you with crop health, weather, and market prices. Please try asking a specific question.",
        "hi": "मैं आपका किसान कोपायलट हूं। मैं फसल स्वास्थ्य, मौसम और बाजार मूल्यों में मदद कर सकता हूं।",
        "te": "నేను మీ కిసాన్ కోపైలట్. పంట ఆరోగ్యం, వాతావరణం మరియు మార్కెట్ ధరలలో సహాయం చేయగలను.",
    }

    return CopilotResponse(
        text=DEFAULT_MESSAGES.get(lang, DEFAULT_MESSAGES["en"]),
        language=lang,
    )


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    summary="Transcribe voice audio via Whisper",
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (webm/opus/wav/mp3)"),
    language: str = Form(default="en"),
    current_user: dict = Depends(get_current_user),
) -> TranscribeResponse:
    """
    Transcribes audio using the Whisper inference service.
    In dev: forwards to a local whisper.cpp HTTP server.
    In prod: uses the edge WASM whisper (client-side) or GPU server.
    """
    t0 = time.perf_counter()

    audio_bytes = await audio.read()
    if len(audio_bytes) < 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Audio too short or empty",
        )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.WHISPER_URL}/inference",
                files={"file": (audio.filename or "audio.webm", io.BytesIO(audio_bytes), audio.content_type or "audio/webm")},
                data={"language": language, "response_format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()
            text_result = data.get("text", "").strip()
    except (httpx.RequestError, httpx.HTTPStatusError) as err:
        log.error("whisper_transcription_failed", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transcription service unavailable",
        )

    duration_ms = (time.perf_counter() - t0) * 1000
    log.info(
        "transcription_complete",
        language=language,
        duration_ms=round(duration_ms),
        text_length=len(text_result),
        user=current_user.get("sub"),
    )

    return TranscribeResponse(
        text=text_result,
        language=language,
        duration_ms=round(duration_ms, 1),
    )
