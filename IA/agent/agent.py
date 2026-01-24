import os
from dotenv import load_dotenv
from pathlib import Path

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.ollama import Ollama

from .tools import tool_class_retriever, tool_retriever

load_dotenv()
MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

async def create_agent(type) -> Agent:
    """
    Creates an instance of an agent
    
    :return: Created agent
    :rtype: Agent
    """ 
    if type=="identifier_agent":
        tool_list=[tool_class_retriever]
        agent_name="JuriAssistant"
        prompt_file = Path(__file__).parent / "prompt.md"
        with open(prompt_file, "r") as f:
            instruction_text = f.read()
    elif type=="chat_agent":
        tool_list=[]
        agent_name="ChatAgent"
        prompt_file = Path(__file__).parent / "chat_prompt.md"
        with open(prompt_file, "r") as f:
            instruction_text = f.read()
    else:
        raise TypeError("Agent type specified does not exist.")
    
    agent = Agent(
        name=agent_name,
        model=Ollama(MODEL, host=OLLAMA_BASE_URL),
        db=InMemoryDb(),
        add_history_to_context=True,
        tools=tool_list,
        instructions=instruction_text,
    )

    return agent
