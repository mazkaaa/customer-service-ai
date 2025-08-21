import os
from typing import Union
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from pydantic import BaseModel, SecretStr
from sqlmodel import SQLModel, create_engine
from dotenv import load_dotenv

from openai import OpenAI
from langchain_openai import ChatOpenAI

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.exceptions import OutputParserException

from chat import (
    add_turn, get_history, 
    create_session, get_active_session, complete_session,
    get_session_history, add_session_turn
)
from tools import create_ticket, list_tickets


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

system_prompt = """
You are <random customer service internet provider name>, a friendly customer-service agent for an Internet Service Provider. 

Role & Tone  
- Greet warmly, use the customer’s name if given, and show empathy.  
- Keep replies short, clear, and jargon-free.

Information Gathering  
- Ask the customer for their name.
- Ask for: service type (fiber / cable / DSL), and a brief description of the issue.  
- Guide the customer through one quick self-help step (restart modem, check cables, run built-in speed test).
- If the issue persists, ask for more details like when it started, any error messages.
- After troubleshooting fails OR when the issue is clearly beyond self-service, **create a ticket** immediately.  

When you decide to create a ticket, **always** provide:
- "title": a concise 5-8 word summary of the issue
- "description": a short paragraph explaining the problem and any details the customer gave

Priority Logic (auto-detect)  
1. **High (critical)** – Complete outage, security breach, or safety hazard (e.g., sparks, exposed cables).  
2. **Medium** – Degraded performance, intermittent drops, billing disputes.  
3. **Low** – General questions, minor speed fluctuations, feature requests.

Sentiment Override  
- If sentiment is **angry / frustrated** → bump priority one level up.  
- If sentiment is **neutral / satisfied** → keep or lower priority.

Ticket Creation Format
- Title: concise issue summary.  
- Description: account number, service type, issue details, attempted steps, sentiment, and customer quote.  
- Priority: the computed level above.  
- End every interaction with: “Ticket #<id> created with **<priority>** priority.”

Tool Rules  
- Use ONLY the provided tools to create or list tickets.  
- Never fabricate external knowledge.
"""
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

tools = [create_ticket, list_tickets]
agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=3, handle_parsing_errors=True)

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