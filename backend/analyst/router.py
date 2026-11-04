"""
AgroTrack AI — AI Analyst API Router
Exposes endpoints for cross-platform grounded conversational queries,
analytical capabilities catalog, and authorised tenant context summary.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status

from backend.models import (
    UserProfile,
    AnalystQueryRequest,
    AnalystQueryResponse,
    AnalystCapability,
)
from backend.security import get_current_user
from backend.analyst import service

router = APIRouter(prefix="/api/v1/analyst", tags=["AI Analyst"])


@router.post("/query", response_model=AnalystQueryResponse)
async def query_analyst(
    request: AnalystQueryRequest,
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Submits an analytical inquiry to the AI Analyst.
    Enforces permission-aware context retrieval, tenant isolation,
    PII sanitization, prompt injection defense, and grounded source attribution.
    """
    return service.process_analyst_query(request, current_user)


@router.get("/capabilities", response_model=List[AnalystCapability])
async def list_capabilities(
    current_user: UserProfile = Depends(get_current_user),
):
    """Lists the supported analytical domains and example questions for the AI Analyst."""
    return service.get_analyst_capabilities()


@router.get("/context-summary", response_model=Dict[str, Any])
async def get_context_summary(
    current_user: UserProfile = Depends(get_current_user),
):
    """Returns an audit of authorised platform records currently accessible to the user."""
    return service.get_user_context_summary(current_user)
