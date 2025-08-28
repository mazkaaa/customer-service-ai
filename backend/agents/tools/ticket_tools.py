import os
from typing import List, Dict
from dotenv import load_dotenv
from redis import Redis
import redis
from sqlmodel import Session, create_engine, desc, select
from models import Ticket
from langchain_core.tools import tool, ToolException

# Load environment variables from .env file
load_dotenv()

database_url = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set.")
engine = create_engine(database_url, echo=False)

if not REDIS_URL:
  raise ValueError("REDIS_URL value variable is not set")

r: Redis = redis.from_url(REDIS_URL, decode_responses=True)

@tool(
    name_or_callable="create_ticket",
    description=(
        "MUST be used to create a new support ticket for a customer. "
        "Do NOT fabricate ticket creation—always call this tool to create a ticket. "
        "Requires: title (concise summary), description (detailed issue), customer_id (identifier), and priority (low, medium, high). "
        "Returns the ticket_number and priority."
    ),
    args_schema={
        "title": "A concise 5-8 word summary of the issue (required)",
        "description": "A short paragraph explaining the problem and any details the customer gave (required)",
        "customer_id": "The customer's phone number, email, or UUID (required)",
        "priority": "The priority of the ticket (low, medium, high). Use the logic in the system prompt."
    },
    return_direct=False
)
def create_ticket(title: str, description: str, customer_id: str, priority: str = "medium") -> str:
    try:
        with Session(engine) as session:
            max_ticket_number = session.exec(
                select(Ticket.ticket_number).order_by(desc(Ticket.ticket_number))
            ).first()
            next_ticket_number = (max_ticket_number or 0) + 1
            ticket = Ticket(
                title=title,
                description=description,
                customer_id=customer_id,
                priority=priority.lower(),
                ticket_number=next_ticket_number
            )
            session.add(ticket)
            session.commit()
            return f"Ticket #{ticket.ticket_number} created with priority {priority}."
    except Exception as e:
        raise ToolException(f"DB error: {str(e)}")

@tool(
    name_or_callable="list_tickets",
    description=(
        "MUST be used to retrieve a list of all tickets with a specific status (open, closed, escalated). "
        "Do NOT fabricate ticket lists—always call this tool to get ticket data. "
        "Returns a list of ticket details."
    ),
    args_schema={
        "status": "The status of the tickets to list (open, closed, escalated)"
    },
    return_direct=True,
)
def list_tickets(status: str = "open") -> List[Dict]:
    with Session(engine) as session:
        stmt = select(Ticket).where(Ticket.status == status.lower())
        rows = session.exec(stmt).all()
        return [
            {"id": t.id, "title": t.title, "ticket_number": t.ticket_number, "description": t.description,
             "priority": t.priority, "status": t.status, "created_at": t.created_at}
            for t in rows
        ]

@tool(
    name_or_callable="update_session_customer_id",
    description=(
        "MUST be used to update the customer_id for the current session when the customer provides their ID. "
        "Do NOT assume the session is updated—always call this tool to set the customer_id for the session. "
        "This ensures the session is linked to the correct customer."
    ),
    args_schema={
        "session_id": "The session ID to update (required)",
        "customer_id": "The customer ID to set (required)"
    },
    return_direct=False
)
def update_session_customer_id(session_id: str, customer_id: str):
    """Update the customer_id for a session and add to customer_sessions index."""
    r.hset(f"session:{session_id}", "customer_id", customer_id)
    r.lpush(f"customer_sessions:{customer_id}", session_id)
