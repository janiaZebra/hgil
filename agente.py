import os
import importlib
from typing import Dict, List
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools.base import Tool
import config

PERSONALITY = os.getenv("PERSONALITY", config.PERSONALITY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODELO_AGENTE = os.getenv("MODELO_AGENTE", config.MODELO_AGENTE)
TEMPERATURE_MODELO = float(os.getenv("TEMPERATURE_MODELO", config.TEMPERATURE_MODELO))
TOOLS_FOLDER = os.path.join(os.path.dirname(__file__), "tools")

def load_tools() -> List[Tool]:
    tools = []
    for filename in os.listdir(TOOLS_FOLDER):
        if filename.startswith("__") or not filename.endswith(".py"):
            continue
        module_name = filename[:-3]
        file_path = os.path.join(TOOLS_FOLDER, filename)
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "get_tools"):
                loaded = module.get_tools()
                if isinstance(loaded, list):
                    tools.extend(loaded)
        except Exception as e:
            print(f"Error al cargar herramienta {filename}: {e}")
    return tools

TOOLS = load_tools()


class AgentManager:
    def __init__(self):
        self.session_memories: Dict[str, ConversationBufferMemory] = {}
        self.agents: Dict[str, AgentExecutor] = {}

    def get_memory(self, session_id):
        if session_id not in self.session_memories:
            self.session_memories[session_id] = ConversationBufferMemory(
                memory_key="chat_history", return_messages=True
            )
        return self.session_memories[session_id]

    def create_agent(self, session_id):
        llm = ChatOpenAI(
            model=MODELO_AGENTE,
            temperature=TEMPERATURE_MODELO,
            openai_api_key=OPENAI_API_KEY
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", PERSONALITY),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad", optional=True),
        ])
        agent = create_openai_functions_agent(
            llm=llm, tools=TOOLS, prompt=prompt
        )
        agent_executor = AgentExecutor(
            agent=agent,
            tools=TOOLS,
            memory=self.get_memory(session_id),
            verbose=True
        )
        self.agents[session_id] = agent_executor
        return agent_executor

    def refresh_agent(self, session_id):
        if session_id in self.agents:
            self.agents[session_id].memory = self.get_memory(session_id)
            return self.agents[session_id]
        return self.create_agent(session_id)


agent_manager = AgentManager()


def chat(session_id: str, message: str):
    response = agent_manager.refresh_agent(session_id) \
        .invoke({"input": message}) \
        .get("output", "Error al obtener la respuesta.") \
        .replace("```", "")
    return response
