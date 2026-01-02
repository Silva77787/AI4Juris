import os
from dotenv import load_dotenv
from pathlib import Path

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.ollama import Ollama
from agno.models.ollama import Ollama

from tools import tool_retriever

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL")

with open("./prompt.md", "r") as f:
    instruction_text = f.read()

async def run_agent(file_path: str):
    agent = Agent(
        name="JuriAssistant",
        model=Ollama(MODEL),
        db=InMemoryDb(),
        add_history_to_context=True,
        tools=[tool_retriever],
        instructions=instruction_text,
    )

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError
    
    document_text = path.read_text(encoding="utf-8")

    prompt = f"""Foi-lhe atribuido o seguinte documento para identificação:
            {document_text}
            """

    await agent.aprint_response(prompt, stream=True)