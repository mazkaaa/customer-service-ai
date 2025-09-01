import os
import re
import shutil
from typing import Union
import uuid
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, File, HTTPException, UploadFile
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, SecretStr
from sqlmodel import SQLModel, create_engine
from dotenv import load_dotenv

from agent import (
    create_session, complete_session,
    get_session_history, add_session_turn,
    ChatOpenAI, AGENT_REGISTRY
)
from langchain_core.exceptions import OutputParserException
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from api.ticket_api import list_tickets
from chat import is_session_completed


# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "moonshotai/kimi-k2:free")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "nvidia/nv-embedqa-mistral-7b-v2")
EMBEDDING_URL = os.getenv("EMBEDDING_URL")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set")
if not EMBEDDING_API_KEY:
    raise ValueError("EMBEDDING_API_KEY environment variable is not set")
if not EMBEDDING_URL:
    raise ValueError("EMBEDDING_URL environment variable is not set")

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

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

embedding_model = NVIDIAEmbeddings(
    model=EMBEDDING_MODEL_NAME,
    api_key=SecretStr(EMBEDDING_API_KEY),
    truncate="NONE",
)

vectorstore = Chroma(
    collection_name="customer_service_knowledge",
    embedding_function=embedding_model,
    persist_directory="./chroma_db",
)

# Only require question at start; customer_id will be asked by AI
class Ask(BaseModel):
    question: str

class SessionAsk(BaseModel):
    question: str
    session_id: str

@app.on_event("startup")
def startup_event():
    """Load existing vectorstore on startup."""
    vectorstore = Chroma(
        collection_name="customer_service_knowledge",
        embedding_function=embedding_model,
        persist_directory="./chroma_db",
    )
    print("Vectorstore loaded.")

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

        # TODO: Check if ticket was created using redis session check (add ticket_id to session on creation)
        if "#" in response["output"]:
            ticket_match = re.search(r"#([\w-]+)", response["output"], re.IGNORECASE)
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

@app.post(
        path="/knowledge",
        tags=["Knowledge Management"]
)
async def upload_knowledge_file(file: UploadFile = File(...)):
    """Upload raw file for knowledge base usages without processing and storing in vector DB."""
    try:
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        file.file.close()
        return {
            "filename": file.filename,
            "message": "File uploaded successfully."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to upload the file. Error: {str(e)}"
            }
        )

@app.put(
        path="/knowledge",
        tags=["Knowledge Management"]
)
async def process_knowledge_by_name(file_name: str):
    """Process an uploaded file by filename and add to vector DB."""
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail={"message": "File not found."}
        )
    
    try:
        loader = PyPDFLoader(file_path)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )
        docs = loader.load()
        all_splits = text_splitter.split_documents(docs)

        vectorstore.add_documents(all_splits)

        return {
            "filename": file_name,
            "chunks_added": len(all_splits),
            "message": "File processed and added to knowledge base."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to process the file. Error: {str(e)}"
            }
        )

@app.get(
        path="/knowledge",
        tags=["Knowledge Management"]
)
async def get_knowledge_list_files():
    """List all uploaded files in the knowledge base. Return filename, extension, is processed, upload date, size, and number of chunks if its processed."""
    try:
        files = []
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                is_processed = len(vectorstore.similarity_search(filename, k=1)) > 0
                files.append({
                    "filename": filename,
                    "extension": os.path.splitext(filename)[1],
                    "is_processed": is_processed,
                    "upload_date": os.path.getctime(file_path),
                    "size_bytes": size,
                    "chunks_in_vector_db": len(vectorstore.similarity_search(filename, k=1000)) if is_processed else 0
                })
        return {"files": files}
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Uploads directory not found."
            }
        )

@app.delete(
        path="/knowledge/{file_name}",
        tags=["Knowledge Management"],
)
async def delete_knowledge_file(file_name: str):
    """Delete an uploaded knowledge file by filename including its chunks in vector DB and the original file."""
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail={"message": "File not found."}
        )
    
    try:
        # Remove from vectorstore
        vectorstore.delete(
            ids=[file_name],
        )
        
        # Remove the original file
        os.remove(file_path)

        return {
            "filename": file_name,
            "message": "File and its knowledge chunks deleted successfully."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to delete the file. Error: {str(e)}"
            }
        )
