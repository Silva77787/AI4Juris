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

async def create_agent(type) -> Agent:
    """
    Creates an instance of an agent
    
    :return: Created agent
    :rtype: Agent
    """ 
    if type=="identifier_agent":
        tool_list=[tool_class_retriever]
        agent_name="JuriAssistant"
        with open("agent/prompt.md", "r") as f:
            instruction_text = f.read()
    elif type=="chat_agent":
        tool_list=[]
        agent_name="ChatAgent"
        with open("agent/chat_prompt.md", "r") as f:
            instruction_text = f.read()
    else:
        raise TypeError("Agent type specified does not exist.")
    
    agent = Agent(
        name=agent_name,
        model=Ollama(MODEL),
        db=InMemoryDb(),
        add_history_to_context=True,
        tools=tool_list,
        instructions=instruction_text,
    )

    return agent
