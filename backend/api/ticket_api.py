
import os
from typing import Dict, List
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select

from models import Ticket

# Load environment variables from .env file
load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set.")
engine = create_engine(database_url, echo=False)

def list_tickets(status: str = "open") -> List[Dict]:
    """List all tickets with a specific status."""
    with Session(engine) as session:
        stmt = select(Ticket).where(Ticket.status == status.lower())
        rows = session.exec(stmt).all()
        return [
            {"id": t.id, "customer_id": t.customer_id, "ticket_number": t.ticket_number, "title": t.title, "description": t.description,
             "priority": t.priority, "status": t.status, "created_at": t.created_at}
            for t in rows
        ]