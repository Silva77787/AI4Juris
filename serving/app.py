from pathlib import Path
from fastapi import FastAPI, HTTPException
from uuid import uuid4
from pydantic import BaseModel

from agent import agent
from dgsi_scraper import knn_predict_from_file

app = FastAPI()
SESSIONS = {}

class IdentifyReq(BaseModel):
    path: str

class CreateChatReq(BaseModel):
    path: str

class ChatReq(BaseModel):
    session_id: str
    message: str

class CloseReq(BaseModel):
    session_id: str

@app.post("/identify")
async def identify(req: IdentifyReq):
    path = Path(req.path) #file to be identified
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    document_text = path.read_text(encoding="utf-8")

    decision = knn_predict_from_file.predict_label_from_text(text=document_text)

    prompt = f"""Foi-lhe atribuido o seguinte documento e decisão:\n
    {document_text}\n
    {decision}
    """

    identifier_agent = await agent.create_agent("identifier_agent")
    
    resp = await identifier_agent.arun(prompt)
    return {"decision": decision, "response": resp}

@app.post("/create_chat")
async def create_chat(req: CreateChatReq):
    path = Path(req.path) #file being questioned about
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    document_text = path.read_text(encoding="utf-8")

    chat_agent = await agent.create_agent("chat_agent")
    await chat_agent.arun(f"Documento base:\n{document_text}")

    session_id = str(uuid4())
    SESSIONS[session_id] = chat_agent
    return {"session_id": session_id}

@app.post("/chat")
async def chat(req: ChatReq):
    agent = SESSIONS.get(req.session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await agent.arun(req.message)
    return {"response": result}

@app.post("/close_chat")
async def close_chat(req: CloseReq):
    agent = SESSIONS.pop(req.session_id, None)
    return {"ok": True}