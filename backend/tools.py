import os
from dotenv import load_dotenv
from sqlmodel import Session, select, create_engine
from models import Ticket
from typing import List, Dict
from langchain_core.tools import tool, ToolException

# Load environment variables from .env file
load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set.")
engine = create_engine(database_url, echo=False)

@tool(name_or_callable="create_ticket", description="Create a new support ticket for a customer with title, description, customer_id, and priority", args_schema={
    "title": "The title of the ticket",
    "description": "A detailed description of the issue",
    "customer_id": "The customer's phone number, email, or UUID",
    "priority": "The priority of the ticket (low, medium, high)"
}, return_direct=False)
def create_ticket(title: str, description: str, customer_id: str, priority: str = "medium") -> str:
    try:
        with Session(engine) as session:
            ticket = Ticket(title=title, description=description, customer_id=customer_id, priority=priority.lower())
            session.add(ticket)
            session.commit()
            return f"Ticket #{ticket.id} created with priority {priority}."
    except Exception as e:
        raise ToolException(f"DB error: {str(e)}")

@tool(name_or_callable="list_tickets", description="List all tickets with a specific status.", args_schema={
    "status": "The status of the tickets to list (open, closed, escalated)"}, return_direct=True)
def list_tickets(status: str = "open") -> List[Dict]:
    with Session(engine) as session:
        stmt = select(Ticket).where(Ticket.status == status.lower())
        rows = session.exec(stmt).all()
        return [
            {"id": t.id, "title": t.title, "description": t.description,
             "priority": t.priority, "status": t.status, "created_at": t.created_at}
            for t in rows
        ]