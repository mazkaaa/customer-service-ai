import os
import re
from typing import Union
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, SecretStr
from sqlmodel import SQLModel, create_engine
from dotenv import load_dotenv

from agent import (
    create_session, complete_session,
    get_session_history, add_session_turn,
    ChatOpenAI, AGENT_REGISTRY
)
from langchain_core.exceptions import OutputParserException

from api.ticket_api import list_tickets
from chat import is_session_completed


# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "moonshotai/kimi-k2:free")

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
    model=MODEL_NAME,
    temperature=0.2,
    default_headers={
        "HTTP-Referer": "localhost:3000",
        "X-Title": "Customer Service AI",
    },
    max_retries=3,
)
agent_executor = AGENT_REGISTRY["customer_service"](llm)

# Only require question at start; customer_id will be asked by AI
class Ask(BaseModel):
    question: str

class SessionAsk(BaseModel):
    question: str
    session_id: str



@app.post("/start")
async def start(payload: Ask):
    """Start a new chat session. The AI will ask for customer_id if not provided."""
    # Create a session without customer_id
    session_id = create_session(None)
    add_session_turn(session_id, "user", payload.question)

    # AI should ask for customer_id if not present
    try:
        response = agent_executor.invoke({
            "input": payload.question,
            "chat_history": [],
            "customer_id": None,
            "session_id": session_id
        })
        add_session_turn(session_id, "assistant", response["output"])
        return {
            "session_id": session_id,
            "output": response["output"],
            "message": "New chat session started."
        }
    except Exception as e:
        ai_error_message = "⚠️  Sorry, I ran into a problem and couldn't process your request. Please try again later."
        raise HTTPException(
            status_code=500,
            detail={
                "session_id": session_id,
                "output": ai_error_message,
                "message": f"Backend error: {str(e)}"
            }
        )


@app.post("/chat")
async def chat(payload: SessionAsk):
    """Continue chat in a session."""
    history = get_session_history(payload.session_id)

    # check if session is already completed, if so, return error
    if is_session_completed(payload.session_id):
        raise HTTPException(
            status_code=400,
            detail={
                "output": "This session has already been completed. Please start a new session for further assistance.",
                "session_id": payload.session_id,
                "session_completed": True,
                "message": "Session already completed."
            }
        )

    try:
        response = agent_executor.invoke({
            "input": payload.question,
            "chat_history": history,
            "session_id": payload.session_id
        })

        add_session_turn(payload.session_id, "user", payload.question)
        add_session_turn(payload.session_id, "assistant", response["output"])

        if "Ticket #" or "ticket #" in response["output"]:
            ticket_match = re.search(r"ticket #([\w-]+)", response["output"], re.IGNORECASE)
            if ticket_match:
                ticket_id = ticket_match.group(1)
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
        ai_error_message = "⚠️  Sorry, I ran into a problem and couldn't process your request. Please try again later."
        raise HTTPException(
            status_code=500,
            detail={
                "output": ai_error_message,
                "session_id": payload.session_id,
                "session_completed": False,
                "message": f"Backend error: {str(e)}"
            }
        )

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session history."""
    history = get_session_history(session_id)
    return {"session_id": session_id, "history": history}
        

@app.get("/tickets")
async def get_tickets(status: str = "open"):
    """
    List tickets, optionally filtered by status.
    """
    tickets = list_tickets(status)
    return {"tickets": tickets}

@app.get("/health")
async def health():
    return {"status": "ok"}