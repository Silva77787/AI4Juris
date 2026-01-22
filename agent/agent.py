import os
from dotenv import load_dotenv
from pathlib import Path

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.ollama import Ollama
from agno.models.ollama import Ollama

from .tools import tool_class_retriever, tool_retriever

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL")

with open("agent/prompt_decision.md", "r") as f:
    instruction_text = f.read()

async def create_agent(type) -> Agent:
    """
    Creates an instance of a RAG agent
    
    :return: Created agent
    :rtype: Agent
    """
    agent = Agent(
        name="JuriAssistant",
        model=Ollama(MODEL),
        db=InMemoryDb(),
        add_history_to_context=True,
        tools=[tool_class_retriever],
        instructions=instruction_text,
    )
