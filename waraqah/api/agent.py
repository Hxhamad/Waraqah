"""AI Agent endpoint stub."""
from fastapi import APIRouter, HTTPException

from waraqah.core.models import AgentChatRequest

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat")
def agent_chat(request: AgentChatRequest):
    """AI Agent endpoint - stub for future implementation.

    The real agent is a later phase (GLM-5.3-flash backend, tools = the API
    endpoints above). The DB is designed so the agent can read it read-only.
    """
    raise HTTPException(
        status_code=501,
        detail={
            "error": "Agent endpoint not yet implemented",
            "spec": "GLM-5.3-flash backend with tools = API endpoints",
            "message_received": request.message,
            "context_received": request.context,
        },
    )
