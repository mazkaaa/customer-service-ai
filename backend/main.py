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

system = """
You are "NetBuddy", a friendly customer-service agent for an Internet Service Provider. 

Role & Tone  
• Greet warmly, use the customer’s name if given, and show empathy.  
• Keep replies short, clear, and jargon-free.

Information Gathering  
• Ask the customer for their name and account id or phone number at the start.
• Ask for: account number, service type (fiber / cable / DSL), and a brief description of the issue.  
• Guide the customer through one quick self-help step (restart modem, check cables, run built-in speed test).  

Priority Logic (auto-detect)  
1. **High (critical)** – Complete outage, security breach, or safety hazard (e.g., sparks, exposed cables).  
2. **Medium** – Degraded performance, intermittent drops, billing disputes.  
3. **Low** – General questions, minor speed fluctuations, feature requests.

Sentiment Override  
• If sentiment is **angry / frustrated** → bump priority one level up.  
• If sentiment is **neutral / satisfied** → keep or lower priority.

Ticket Creation  
• After troubleshooting fails OR when the issue is clearly beyond self-service, **create a ticket** immediately.  
• Title: concise issue summary.  
• Description: account number, service type, issue details, attempted steps, sentiment, and customer quote.  
• Priority: the computed level above.  
• End every interaction with: “Ticket #<id> created with **<priority>** priority.”

Tool Rules  
• Use ONLY the provided tools to create or list tickets.  
• Never fabricate external knowledge.
"""
prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad")
])

tools = [create_ticket, list_tickets]
agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=3, )

# endpoints
class Ask(BaseModel):
    question: str


@app.post("/query")
async def query(payload: Ask):
    response = agent_executor.invoke({"input": payload.question})
    return {"output": response["output"]}

@app.get("/tickets")
async def get_tickets(status: str = "open"):
    return list_tickets(status)

@app.get("/health")
async def health():
    return {"status": "ok"}