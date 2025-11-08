from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, Message
from app.ai_agent import AIAgent, session_manager

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: int
    message: str
    file_path: Optional[str] = None
    filename: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    action: Optional[str] = None
    data: Optional[dict] = None

@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message to the AI agent"""
    if current_user.id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # If file was uploaded, store it in session
    if request.file_path:
        session = session_manager.get_session(request.user_id)
        data = session.get("data", {})
        data["file_path"] = request.file_path
        data["filename"] = request.filename
        session_manager.update_session(request.user_id, {"data": data})
    
    # Process message through AI agent
    agent = AIAgent(db)
    response_text, action, data = agent.process_message(request.user_id, request.message)
    
    # Save message to database
    user_message = Message(
        sender_id=request.user_id,
        receiver_id=None,
        content=request.message,
        file_path=request.file_path
    )
    db.add(user_message)
    
    # Save AI response to database
    ai_message = Message(
        sender_id=None,
        receiver_id=request.user_id,
        content=response_text
    )
    db.add(ai_message)
    db.commit()
    
    return ChatResponse(
        response=response_text,
        action=action,
        data=data
    )

@router.get("/history")
async def get_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get chat history for current user"""
    messages = db.query(Message).filter(
        (Message.sender_id == current_user.id) | 
        (Message.receiver_id == current_user.id)
    ).order_by(Message.timestamp).all()
    
    history = []
    for msg in messages:
        history.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "file_path": msg.file_path
        })
    
    return {"history": history}

@router.delete("/history")
async def clear_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Clear chat history for current user"""
    db.query(Message).filter(
        (Message.sender_id == current_user.id) | 
        (Message.receiver_id == current_user.id)
    ).delete()
    
    # Also clear session
    session_manager.clear_session(current_user.id)
    
    db.commit()
    return {"message": "Chat history cleared"}