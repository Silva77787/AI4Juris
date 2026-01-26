from pathlib import Path
from fastapi import FastAPI, HTTPException, File, UploadFile
from uuid import uuid4
from pydantic import BaseModel
from typing import List, Dict, Any
import subprocess
import tempfile
from agent import agent
from tfidf_svm import tfidf_svm_predict_from_file

app = FastAPI()
SESSIONS = {}

class IdentifyReq(BaseModel):
    path: str

class IdentifyTextReq(BaseModel):
    text: str

class CreateChatReq(BaseModel):
    path: str

class CreateChatTextReq(BaseModel):
    text: str

class ChatReq(BaseModel):
    session_id: str
    message: str

class CloseReq(BaseModel):
    session_id: str

def _bytes_to_text(filename: str | None, content_type: str | None, raw: bytes) -> str:
    """Convert uploaded bytes to text.

    Supports plain text and PDFs. PDFs are converted via `pdftotext` (poppler-utils).
    """
    name = (filename or "").lower()
    ctype = (content_type or "").lower()

    is_pdf = name.endswith(".pdf") or ("application/pdf" in ctype)

    if is_pdf:
        # Write PDF to a temp file and convert to text using pdftotext.
        with tempfile.TemporaryDirectory() as td:
            pdf_path = Path(td) / "input.pdf"
            txt_path = Path(td) / "output.txt"
            pdf_path.write_bytes(raw)

            # -layout keeps a closer reading order; adjust if you prefer.
            # Output file path is provided so we can read it reliably.
            try:
                subprocess.run(
                    ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except FileNotFoundError:
                raise RuntimeError("pdftotext not found in container. Ensure poppler-utils is installed.")
            except subprocess.CalledProcessError as e:
                msg = e.stderr.decode("utf-8", errors="ignore")
                raise RuntimeError(f"pdftotext failed: {msg}")

            return txt_path.read_text(encoding="utf-8", errors="ignore")

    # Default: treat as text
    return raw.decode("utf-8", errors="ignore")

@app.post("/identify")
async def identify(req: IdentifyReq):
    path = Path(req.path) #file to be identified
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    document_text = path.read_text(encoding="utf-8")

    decision = tfidf_svm_predict_from_file.predict_label_from_text(text=document_text)

    prompt = f"""Foi-lhe atribuido o seguinte documento:\ndecisão:\n
    {document_text}\n
    {decision}
    """

    identifier_agent = await agent.create_agent("identifier_agent")
    
    resp = await identifier_agent.arun(prompt)
    return {"decision": decision, "response": resp}

@app.post("/identify_text")
async def identify_text(req: IdentifyTextReq):
    text = req.text or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    print(f"identify_text received {len(text)} chars")
    print(text[:2000])

    decision = tfidf_svm_predict_from_file.predict_label_from_text(text=text)

    print(f"Predicted decision: {decision}")
    prompt = f"""DECISION:\n
    {decision}
    DOCUMENT TEXT:\n
    {text}\n
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

@app.post("/create_chat_text")
async def create_chat_text(req: CreateChatTextReq):
    text = req.text or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    chat_agent = await agent.create_agent("chat_agent")
    await chat_agent.arun(f"Documento base:\n{text}")

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

@app.post("/predict/tfidf-svm/batch")
async def predict_tfidf_svm_batch(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    results: List[Dict[str, str]] = []

    for f in files:
        try:
            raw = await f.read()
            text = _bytes_to_text(f.filename, getattr(f, "content_type", None), raw)

            label = tfidf_svm_predict_from_file.predict_label_from_text(text=text)

            results.append({"filename": f.filename or "(unnamed)", "label": label})
        except Exception as e:
            results.append({"filename": f.filename or "(unnamed)", "error": str(e)})

    return {"predictions": results}