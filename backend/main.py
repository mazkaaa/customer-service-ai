import os
from typing import Union
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from pydantic import BaseModel, SecretStr
from sqlmodel import SQLModel, create_engine
from dotenv import load_dotenv

from agent import (
    create_session, get_active_session, complete_session,
    get_session_history, add_session_turn,
    create_ticket, list_tickets,
    ChatOpenAI, AGENT_REGISTRY
)
from langchain_core.exceptions import OutputParserException


# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set")

engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)

app = FastAPI(
    title="Customer Service AI",
    description="A simple customer service AI backend",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Instantiate the customer service agent from the registry
llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=SecretStr(OPENROUTER_API_KEY),
    model="moonshotai/kimi-k2:free",
    temperature=0.2,
    default_headers={
        "HTTP-Referer": "localhost:3000",
        "X-Title": "Customer Service AI",
    },
    max_retries=3,
)
agent_executor = AGENT_REGISTRY["customer_service"](llm)

# endpoints
class Ask(BaseModel):
    question: str
    customer_id: str

class SessionAsk(BaseModel):
    question: str
    session_id: str


@app.post("/start")
async def start(payload: Ask):
    """Start a new chat session for a customer."""
    # Always create a new session when starting
    session_id = create_session(payload.customer_id)
    add_session_turn(session_id, "user", payload.question)
    
    # Get AI response for the initial question
    try:
        response = agent_executor.invoke({"input": payload.question, "chat_history": []})
        add_session_turn(session_id, "assistant", response["output"])
        
        return {
            "session_id": session_id, 
            "output": response["output"],
            "message": "New chat session started."
        }
    except Exception as e:
        return {
            "session_id": session_id,
            "output": f"⚠️  I ran into a problem: {e}. Please try again later.",
            "message": "New chat session started."
        }

@app.post("/chat")
async def chat(payload: SessionAsk):
    """Continue chat in a session."""
    history = get_session_history(payload.session_id)
    
    try:
        response = agent_executor.invoke({"input": payload.question, "chat_history": history})
        
        add_session_turn(payload.session_id, "user", payload.question)
        add_session_turn(payload.session_id, "assistant", response["output"])
        
        # Check if ticket was created and complete session
        if "Ticket #" in response["output"]:
            # Extract ticket ID from response
            import re
            ticket_match = re.search(r"Ticket #(\d+)", response["output"])
            if ticket_match:
                ticket_id = int(ticket_match.group(1))
                complete_session(payload.session_id, ticket_id)
                return {
                    "output": response["output"], 
                    "session_id": payload.session_id,
                    "session_completed": True,
                    "ticket_id": ticket_id
                }
        
        return {
            "output": response["output"], 
            "session_id": payload.session_id,
            "session_completed": False
        }
    except Exception as e:
        return {"output": f"⚠️  I ran into a problem: {e}. Please try again later."}

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session history."""
    history = get_session_history(session_id)
    return {"session_id": session_id, "history": history}
        

@app.get("/tickets")
async def get_tickets(status: str = "open"):
    return list_tickets(status)

@app.get("/health")
async def health():
    return {"status": "ok"}