from datetime import date
from typing import  Any
import logging
from collections.abc import AsyncIterable

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from nico_agent_langgraph.app.tools.availability import get_availability
from nico_agent_langgraph.app.models.agent_response import ResponseFormat

logger = logging.getLogger("NicoAgent")
logger.setLevel(logging.INFO)

memory = MemorySaver()

class NicoAgent:
    """ NicoAgent - An agent to manage Nico's availability. """

    SUPPORTED_CONTENT_TYPES = ["text/plain", "text"]

    SYSTEM_INSTRUCTION = (
        "Eres el asistente de agenda de Nico. "
        "Tu único propósito es usar la herramienta `get_availability` para responder preguntas sobre el horario de Nico para jugar al baloncesto. "
        "Se te proporcionará la fecha actual para ayudarte a entender consultas de fechas relativas como 'mañana' o 'la próxima semana'. "
        "Usa esta información para llamar correctamente a la herramienta con una fecha específica (ej: 'AAAA-MM-DD'). "
        "Si el usuario pregunta sobre cualquier cosa que no sea programar baloncesto, "
        "indica cortésmente que no puedes ayudar con ese tema y que solo puedes asistir con consultas de agenda. "
        "No intentes responder preguntas no relacionadas ni usar herramientas para otros propósitos. "
        "Establece el estado de la respuesta (status) a `input_required` si el usuario necesita proporcionar más información. "
        "Establece el estado de la respuesta a `error` si ocurre un error al procesar la solicitud. "
        "Establece el estado de la respuesta a `completed` si la solicitud está completa."
    )

    def __init__(self):
        logger.info("Inicializando NicoAgent y configurando LangGraph...")

        self.model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
        self.tools = [get_availability]

        self.graph = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.SYSTEM_INSTRUCTION,
            checkpointer=memory,
            response_format=ResponseFormat,
        )

        logger.debug("Grafo de NicoAgent creado exitosamente.")

    def invoke(self, query, context_id):
        """
        Executes the agent synchronously, injecting current date context and returning the final processed response.     
        """
        logger.info(f"INVOKE: Iniciando ejecución síncrona. ContextID: {context_id}")
        config: RunnableConfig = {"configurable":{"thread_id": context_id}}

        today_str = f"La fecha de hoy es {date.today().strftime("%Y-%m-%d")}."
        argumented_query = f"{today_str}\n\nUser query: {query}"

        logger.debug(f"Query argumentada enviada al grafo: {argumented_query}")

        self.graph.invoke({"messages": [("user", argumented_query)]}, config=config)

        logger.info("Ejecución síncrona finalizada. Obteniendo respuesta estructurada.")
        return self.get_agent_response(config)
    
    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        """
        Executes the agent asynchronously, yielding a stream of events that includes intermediate status updates and the final response
        """
        logger.info(f"STREAM START: Iniciando stream asíncrono. ContextID: {context_id}")

        today_str = f"La fecha de hoy es {date.today().strftime('%Y-%m-%d')}."
        augmented_query = f"{today_str}\n\nUser query: {query}"
        inputs = {"messages": [("user", augmented_query)]}
        config: RunnableConfig = {"configurable": {"thread_id": context_id}}

        for item in self.graph.stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                tool_name = message.tool_calls[0].get("name", "unknown")
                logger.info(f"El agente está intentando usar la herramienta: {tool_name}")
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Checking Nico's availability...",
                }
            elif isinstance(message, ToolMessage):
                logger.info("Respuesta de herramienta recibida. Procesando siguiente paso...")
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Processing availability...",
                }
        
        logger.info("Stream de LangGraph finalizado. Generando respuesta final.")
        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        """
        Retrieves and parses the final structured response from the agent's graph state.

        This method extracts the 'structured_response' generated by the LLM from the 
        current graph state, interprets its status (input_required, completed, error), 
        and normalizes it into a client-ready dictionary.

        Args:
            config (RunnableConfig): Configuration dictionary containing the 'thread_id'
                                     needed to access the specific conversation state.

        Returns:
            dict: A standardized dictionary containing:
                - "is_task_complete" (bool): True if the request is fully resolved.
                - "require_user_input" (bool): True if the agent needs more details.
                - "content" (str): The message to be displayed to the user.
        """
        logger.debug("Consultando estado final del grafo para extraer 'structured_response'...")
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get("structured_response")

        if structured_response:
            logger.debug("Respuesta estructurada encontrada")

        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == "input_required":
                logger.info("Respuesta final: INPUT_REQUIRED.")
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message,
                }
            if structured_response.status == "error":
                logger.warning("Respuesta final: ERROR detectado por el agente.")
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message,
                }
            if structured_response.status == "completed":
                logger.info("Respuesta final: COMPLETED. Tarea finalizada exitosamente.")
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": structured_response.message,
                }

        logger.error("FALLO CRÍTICO: No se encontró 'structured_response' válida en el estado del grafo.")
        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": (
                "No podemos procesar su solicitud en este momento. "
                "Por favor, inténtelo de nuevo más tarde."
            ),
        }