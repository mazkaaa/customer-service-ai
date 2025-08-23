from chat import (
    create_session, get_active_session, complete_session,
    get_session_history, add_session_turn
)
from agents.tools.ticket_tools import create_ticket, list_tickets
from langchain_openai import ChatOpenAI
from agents.customer_service_agent import get_customer_service_agent

# Registry for all agents (expandable for multi-agent)
AGENT_REGISTRY = {
    "customer_service": get_customer_service_agent
}

__all__ = [
    "create_session", "get_active_session", "complete_session",
    "get_session_history", "add_session_turn",
    "create_ticket", "list_tickets",
    "ChatOpenAI", "AGENT_REGISTRY"
]
