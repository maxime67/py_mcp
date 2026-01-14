import asyncio
from typing import List, Dict, Any, Type

from langchain.globals import set_debug
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI
from mcp_use import MCPClient
from pydantic import BaseModel, Field, create_model

set_debug(True)

# --- Configuration pour LM Studio Server ---
LLM_CHAT_SERVER_BASE_URL = "http://127.0.0.1:1234/v1"
LLM_CHAT_MODEL = "openai/gpt-oss-20b" # ou "meta-llama-3.1-8b-instruct"
LLM_CHAT_TEMPERATURE = 0.3
LLM_CHAT_API_KEY = "not-needed"

agent_executor: AgentExecutor | None = None
mcp_client: MCPClient | None = None

async def build_agent() -> AgentExecutor:
    print("--- 1. Prêt à analyser un film via son ID ---")

    print("\n--- 2. Initialisation du LLM et du client MCP ---")
    llm = ChatOpenAI(
        model=LLM_CHAT_MODEL,
        base_url=LLM_CHAT_SERVER_BASE_URL,
        temperature=LLM_CHAT_TEMPERATURE,
        api_key=LLM_CHAT_API_KEY
    )

    mcp_client = MCPClient.from_config_file("../resources/servers.json")
    session = await mcp_client.create_session("movies-mcp-server")
    print("Connexion au serveur d'outils (MCP) établie.")

    print("\n--- 3. Découverte et création dynamique des outils LangChain ---")
    remote_tools_definitions = await session.list_tools()
    langchain_tools: List[StructuredTool] = []
    type_mapping = {'string': str, 'integer': int, 'number': float, 'boolean': bool, 'object': dict}

    async def run_mcp_tool(tool_name: str, **kwargs: Dict[str, Any]) -> str:
        print(f"--- AGENT -> OUTIL : Appel de '{tool_name}' avec {kwargs} ---")
        result = await session.call_tool(name=tool_name, arguments=kwargs)
        # On formate le dictionnaire de retour en une chaîne de caractères
        # pour que le LLM puisse le lire facilement dans l'étape d'observation.
        text_result = result.content[0].text if result.content else "Action effectuée."
        print(f"--- OUTIL -> AGENT : Résultat : {text_result} ---")
        return text_result


    for tool_def in remote_tools_definitions:
        fields: Dict[str, Any] = {}
        params_schema = tool_def.inputSchema

        if 'properties' in params_schema:
            for param_name, param_details in params_schema['properties'].items():
                if not param_name.startswith('_'):
                    param_type = type_mapping.get(param_details.get('type'), Any)
                    description = param_details.get('description', '')
                    fields[param_name] = (param_type, Field(..., description=description))

        DynamicToolArgs: Type[BaseModel] = create_model(f'{tool_def.name}Args', **fields)
        tool_func = (lambda name: lambda **kwargs: run_mcp_tool(name, **kwargs))(tool_def.name)
        langchain_tool = StructuredTool(
            name=tool_def.name, description=tool_def.description, func=tool_func,
            coroutine=tool_func, args_schema=DynamicToolArgs
        )
        langchain_tools.append(langchain_tool)

    print(f"Outil LangChain créé dynamiquement : {[tool.name for tool in langchain_tools]}")

    print("\n--- 4. Construction de l'agent avec un prompt système adapté ---")
    system_prompt = """
        Tu es un assistant expert en cinéma. Tu dois répondre aux questions de l'utilisateur en français.
        Analyse la question de l'utilisateur. Si tu as besoin d'informations que tu n'as pas, appelle l'outil approprié que tu as à ta disposition.
        Une fois que tu as obtenu une réponse de l'outil, utilise cette information pour formuler une réponse finale et claire pour l'utilisateur.
        """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, langchain_tools, prompt)
    print("Agent Executor prêt.")

    return AgentExecutor(agent=agent, tools=langchain_tools, verbose=True)

async def run_agent():
    # variable globale utile uniquement si par la suite vous souhaitez initialiser l'agent
    # depuis FastAPI via @asynccontextmanager / async def lifespan(app: FastAPI):
    global agent_executor
    print("Démarrage de l'application : initialisation de l'agent...")
    agent_executor = await build_agent()
    print("Agent prêt à transmettre une requête.")
    if agent_executor:
        user_request = "Pour le film avec l'ID 1, peux-tu m'afficher le synopsis pertinent ?"
        response = await agent_executor.ainvoke({"input": user_request})
        print(response.get("output", "Pas de sortie de l'agent."))
    print("Arrêt de l'application : fermeture des sessions MCP...")
    if mcp_client:
        await mcp_client.close_all_sessions()
    print("Sessions fermées.")

async def main():
    await run_agent()

if __name__ == "__main__":
    asyncio.run(main())