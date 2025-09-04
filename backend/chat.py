import json
import os
import uuid
from typing import List, Dict, Any, cast, Optional
from datetime import datetime
from dotenv import load_dotenv
import redis
from redis import Redis

# Load environment variables from .env file
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
  raise ValueError("REDIS_URL value variable is not set")

r: Redis = redis.from_url(REDIS_URL, decode_responses=True)


# Session-based chat functions
def create_session(customer_id: Optional[str]) -> str:
    """Create a new chat session for a customer. customer_id can be None until provided."""
    session_id = str(uuid.uuid4())
    session_data = {
        "customer_id": customer_id if customer_id is not None else "",
        "status": "active",
        "created_at": datetime.utcnow().isoformat()
    }
    r.hset(f"session:{session_id}", mapping=session_data)
    r.expire(f"session:{session_id}", 1800)  # 30 min TTL for active session
    if customer_id:
        r.lpush(f"customer_sessions:{customer_id}", session_id)
    return session_id

def get_active_session(customer_id: str) -> Optional[str]:
    """Get the most recent active session for a customer."""
    sessions = cast(List[str], r.lrange(f"customer_sessions:{customer_id}", 0, -1))
    for session_id in sessions:
        session_data = cast(Dict[str, str], r.hgetall(f"session:{session_id}"))
        if session_data and session_data.get("status") == "active":
            return session_id
    return None

def complete_session(session_id: str, ticket_id: Optional[str] = None) -> bool:
    """Mark a session as completed (delete the session after marking it completed)."""
    try:
        # Check if session exists before attempting to delete
        if r.exists(f"session:{session_id}") == 0:
            return False  # Session doesn't exist
        
        r.delete(f"chat_session:{session_id}")  # Remove chat history after completion
        r.delete(f"session:{session_id}")  # Remove session data
        return True  # Successfully deleted
    except Exception:
        return False  # Failed to delete

def get_session_history(session_id: str) -> List[Dict]:
    """Get chat history for a specific session."""
    data = cast(List[str], r.lrange(f"chat_session:{session_id}", 0, -1))
    if not data:
        return []
    return [json.loads(m) for m in reversed(data)]

def is_session_completed(session_id: str) -> bool:
    """Check if a session is completed (doesn't exist in redis)."""
    return r.exists(f"session:{session_id}") == 0

def add_session_turn(session_id: str, role: str, content: str):
    """Add a message to a session."""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    r.lpush(f"chat_session:{session_id}", json.dumps(message))
    # Reset TTL on activity
    r.expire(f"session:{session_id}", 1800)
    r.expire(f"chat_session:{session_id}", 1800)

def get_history(customer_id: str) -> List[Dict]:
    """
    Retrieve the chat history for a specific customer from Redis.
    
    Args:
        customer_id (str): The ID of the customer whose history is to be retrieved.
    
    Returns:
        List[Dict]: A list of chat messages in the format {'role': 'user' or 'assistant', 'content': str}.
    """
    data = cast(List[str], r.lrange(f"chat:{customer_id}", 0, -1))
    # Ensure data is a list before processing
    if not data:
        return []
    return [json.loads(m) for m in data]

def add_turn(customer_id: str, role: str, content: str):
    """
    Add a new turn to the chat history for a specific customer.
    Args:
        customer_id (str): The ID of the customer.
        role (str): The role of the message sender ('user' or 'assistant').
        content (str): The content of the message.
    """
    
    r.lpush(f"chat:{customer_id}", json.dumps({"role": role, "content": content}))
    # r.ltrim(f"chat:{customer_id}", 0, 19)   # keep 20 messages (10 turns)