"""
Chat router - handles LLM conversation endpoints with session memory
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from services.langchain_service import get_chat_session_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

# Initialize service
chat_service = get_chat_session_service()


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User's message to the AI", min_length=1, max_length=5000)
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: Optional[str] = None
    session_id: str
    message_count: int
    model_used: str
    timestamp: str
    error: Optional[str] = None


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message to the AI and get a response with conversation memory.

    - **message**: Your message to the AI (required)
    - **session_id**: Session ID for conversation continuity (optional, auto-generated if not provided)

    The AI will remember the conversation history within the session.

    Example:
    ```bash
    curl -X POST "http://localhost:8001/chat/message" \
      -H "Content-Type: application/json" \
      -d '{"message": "你好，请介绍一下你自己"}'

    # Continue conversation
    curl -X POST "http://localhost:8001/chat/message" \
      -H "Content-Type: application/json" \
      -d '{"message": "我刚才问了什么？", "session_id": "abc-123"}'
    ```
    """
    try:
        result = await chat_service.chat(
            user_input=request.message,
            session_id=request.session_id
        )

        if result.get("error"):
            return ChatResponse(
                response=None,
                session_id=result.get("session_id", ""),
                message_count=0,
                model_used=chat_service.model_name,
                timestamp=result.get("timestamp", ""),
                error=result.get("error")
            )

        return ChatResponse(
            response=result.get("response"),
            session_id=result.get("session_id", ""),
            message_count=result.get("message_count", 0),
            model_used=result.get("model_used", ""),
            timestamp=result.get("timestamp", "")
        )

    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/history/{session_id}")
async def get_session_history(session_id: str):
    """
    Get all messages in a session's history.

    - **session_id**: The session identifier

    Returns a list of messages with role (user/assistant) and content.

    Example:
    ```bash
    curl "http://localhost:8001/chat/history/abc-123"
    ```
    """
    try:
        messages = chat_service.get_session_history_messages(session_id)
        return {
            "session_id": session_id,
            "messages": messages,
            "message_count": len(messages)
        }
    except Exception as e:
        logger.error(f"Error getting session history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    Clear chat history for a session.

    - **session_id**: The session identifier to clear

    Example:
    ```bash
    curl -X DELETE "http://localhost:8001/chat/session/abc-123"
    ```
    """
    try:
        result = chat_service.clear_session(session_id)
        return result
    except Exception as e:
        logger.error(f"Error clearing session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/sessions")
async def list_sessions():
    """
    Get information about all active chat sessions.

    Returns a list of all sessions with their message counts.

    Example:
    ```bash
    curl "http://localhost:8001/chat/sessions"
    ```
    """
    try:
        sessions = chat_service.get_all_sessions()
        return {
            "total_sessions": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint for chat service."""
    return {
        "status": "healthy",
        "service": "ChatSessionService",
        "model": chat_service.model_name
    }
