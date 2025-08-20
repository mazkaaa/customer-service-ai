import os
from sqlmodel import Session, select, create_engine
from models import Ticket
from typing import List, Dict
from langchain_core.tools import tool

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set.")
engine = create_engine(database_url, echo=False)

@tool
def create_ticket(title: str, description: str, priority: str = "medium") -> str:
    with Session(engine) as session:
        ticket = Ticket(title=title, description=description, priority=priority.lower())
        session.add(ticket)
        session.commit()
        return f"Ticket #{ticket.id} created with priority {priority}."

@tool
def list_tickets(status: str = "open") -> List[Dict]:
    with Session(engine) as session:
        stmt = select(Ticket).where(Ticket.status == status.lower())
        rows = session.exec(stmt).all()
        return [
            {"id": t.id, "title": t.title, "description": t.description,
             "priority": t.priority, "status": t.status, "created_at": t.created_at}
            for t in rows
        ]