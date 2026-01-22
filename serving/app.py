from pathlib import Path
from fastapi import FastAPI, HTTPException
from agent import agent

app = FastAPI()

@app.post("/identify")
def identify(req):
    path = Path(req)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    document_text = path.read_text(encoding="utf-8")
    prompt = f"""Foi-lhe atribuido o seguinte documento para identificação:
    {document_text}
    """

    rag_agent = agent.create_agent()

    resp = rag_agent.arun(prompt)
    return {"response": resp}
