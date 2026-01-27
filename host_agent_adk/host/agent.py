import asyncio
import json
import uuid
import httpx
import logging
import nest_asyncio
from datetime import datetime
from typing import Any, AsyncIterable, List
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from .remote_agent_connection import RemoteAgentConnections

from .basketball_tools import (
    book_basketball_court,
    list_court_availabilities,
)

load_dotenv() 
nest_asyncio.apply()

# Configuracion del formato para ver la hora, el nivel (INFO/ERROR) y el mensaje
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("HostAgent")

class HostAgent:

    def __init__(self):
        logger.info("Inicializando nueva instancia de HostAgent...")
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self._agent = self.create_agent()
        self._user_id = "host_agent"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        logger.debug("Componentes internos de HostAgent (Runner, Servicios) inicializados.")

    async def _async_init_components(self, remote_agent_addresses: List[str]):
        # Inicializa las conexiones a los agentes remotos y obtiene sus tarjetas de agente
        logger.info(f"Iniciando conexión con {len(remote_agent_addresses)} agentes remotos.")

        async with httpx.AsyncClient(timeout=30) as client:
            for address in remote_agent_addresses:
                logger.debug(f"Intentando resolver tarjeta de agente en: {address}")
                card_resolver = A2ACardResolver(client, address)
                try:

                    card = await card_resolver.get_agent_card()
                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card
                    logger.info(f"Conexión exitosa con agente: {card.name} en {address}")

                except httpx.ConnectError as e:
                    logger.error(f"ERROR DE CONEXIÓN: No se pudo conectar con {address}. Detalle: {e}")
                except Exception as e:
                    logger.error(f"ERROR GENERAL: Fallo al inicializar conexión para {address}. Detalle: {e}", exc_info=True)

        # Creamos una lista simplificada de la información de los agentes para las instrucciones raíz
        agent_info = [
            json.dumps({"name": card.name, "description": card.description})
            for card in self.cards.values()
        ]

        if agent_info:
            logger.info(f"Total de agentes amigos conectados: {len(agent_info)}")
            self.agents = "\n".join(agent_info)
        else:
            logger.warning("No se encontraron agentes amigos disponibles (No friends found).")
            self.agents = "No friends found"

    # Crea una instancia de HostAgent de forma asíncrona
    @classmethod
    async def create(
        cls,
        remote_agent_addresses: List[str],
    ):
        logger.info("Creando HostAgent vía método `create`...")
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        logger.info("HostAgent creado y componentes inicializados correctamente.")
        return instance

    # Crea el agente host ADK con las herramientas y la instrucción raíz
    def create_agent(self) -> Agent:
        logger.debug("Configurando definición del Agente ADK (instrucciones y herramientas).")
        return Agent(
            model="gemini-2.5-flash-lite",
            name="Host_Agent",
            instruction=self.root_instruction,
            description="Este agente Anfitrión coordina la planificación de partidos de baloncesto con amigos.",
            tools=[
                self.send_message,
                book_basketball_court,
                list_court_availabilities,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        return f"""
        **Rol:** Eres el Agente Anfitrión, un experto organizador de partidos de baloncesto. 
        Tu función principal es coordinar con los agentes de tus amigos para encontrar un horario adecuado para jugar y luego reservar una cancha.

        **Directrices Principales:**

        * **Iniciar Planificación:** Cuando se te pida organizar un partido, primero determina a quién invitar y el rango de fechas deseado por el usuario.
        * **Delegación de Tareas:** Usa la herramienta `send_message` para preguntar a cada amigo por su disponibilidad.
            * Formula tu solicitud claramente (ej: "¿Estás disponible para jugar baloncesto entre el 2024-08-01 y el 2024-08-03?").
            * Asegúrate de pasar el nombre oficial del agente del amigo para cada solicitud de mensaje.
        * **Analizar Respuestas:** Una vez que tengas la disponibilidad de todos los amigos, analiza las respuestas para encontrar horarios en común.
        * **Verificar Disponibilidad de Cancha:** Antes de proponer horarios al usuario, usa la herramienta `list_court_availabilities` para asegurarte de que la cancha también esté libre en los horarios comunes.
        * **Proponer y Confirmar:** Presenta los horarios comunes que tengan cancha disponible al usuario para su confirmación.
        * **Reservar la Cancha:** Después de que el usuario confirme una hora, usa la herramienta `book_basketball_court` para hacer la reserva. Esta herramienta requiere un `start_time` (hora de inicio) y un `end_time` (hora de fin).
        * **Comunicación Transparente:** Transmite la confirmación final de la reserva, incluyendo el ID de la reserva, al usuario. No pidas permiso antes de contactar a los agentes de los amigos.
        * **Dependencia de Herramientas:** Confía estrictamente en las herramientas disponibles para resolver las solicitudes del usuario. No generes respuestas basadas en suposiciones.
        * **Legibilidad:** Asegúrate de responder en un formato conciso y fácil de leer (las viñetas son buenas).
        * Cada agente disponible representa a un amigo. Así que Fran_Agent representa a Fran, por ejemplo.
        * Cuando se pregunte qué amigos están disponibles, debes devolver los nombres de los amigos disponibles (es decir, los agentes que están activos).

        **Fecha de Hoy (AAAA-MM-DD):** {datetime.now().strftime("%Y-%m-%d")}

        <Agentes Disponibles>
        {self.agents}
        </Agentes Disponibles>
        """

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """
        Streams the agent's response to a given query.
        """
        logger.info(f"Recibida consulta del usuario. SessionID: {session_id} | Query: '{query}'")
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(role="user", parts=[types.Part.from_text(text=query)])

        if session is None:
            logger.info(f"Creando nueva sesión para ID: {session_id}")
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )

        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ""
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = "\n".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                logger.info("Respuesta final generada y enviada al usuario.")
                yield {
                    "is_task_complete": True,
                    "content": response,
                }
            else:
                yield {
                    "is_task_complete": False,
                    "updates": "The host agent is thinking...",
                }

    # Enviamos mensajes a los agentes amigos remotos para delegar tareas
    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        """Sends a task to a remote friend agent."""
        logger.info(f"TOOL CALL: Enviando mensaje a '{agent_name}'. Tarea: {task}")

        if agent_name not in self.remote_agent_connections:
            logger.error(f"Error: El agente '{agent_name}' no se encuentra en las conexiones registradas.")
            raise ValueError(f"Agent {agent_name} not found")
        
        client = self.remote_agent_connections[agent_name]

        if not client:
            logger.error(f"Error: Cliente HTTP no disponible para '{agent_name}'.")
            raise ValueError(f"Client not available for {agent_name}")

        # La generacion del `task_id` se genera automáticamente al enviar el mensaje
        state = tool_context.state
        context_id = state.get("context_id", str(uuid.uuid4()))
        message_id = str(uuid.uuid4())

        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": task}],
                "messageId": message_id,
                "contextId": context_id,
            },
        }

        # Añadimos el taskId si ya existe en el estado para continuar una tarea existente
        task_id = state.get("task_id")
        if task_id:
            payload["message"]["taskId"] = task_id
            logger.debug(f"Continuando tarea existente: {task_id}")

        message_request = SendMessageRequest(
            id=message_id, params=MessageSendParams.model_validate(payload)
        )

        try:
            logger.debug(f"Enviando request a {agent_name} con MessageID: {message_id}")
            send_response: SendMessageResponse = await client.send_message(message_request)
            logger.info(f"Respuesta recibida de '{agent_name}' exitosamente.")

            if not isinstance(
                send_response.root, SendMessageSuccessResponse
            ) or not isinstance(send_response.root.result, Task):
                logger.error("Se recibió una respuesta fallida o que no es una tarea (Task). No se puede continuar.")
                return

            response_content = send_response.root.model_dump_json(exclude_none=True)
            json_content = json.loads(response_content)

            resp = []
            if json_content.get("result", {}).get("artifacts"):
                count_artifacts = len(json_content["result"]["artifacts"])
                logger.info(f"Procesando {count_artifacts} artefactos recibidos de {agent_name}.")

                for artifact in json_content["result"]["artifacts"]:
                    if artifact.get("parts"):
                        resp.extend(artifact["parts"])

            logger.info(f"Retornando {len(resp)} partes de contenido procesado.")
            return resp
        
        except Exception as e:
            logger.error(f"Error al enviar mensaje a '{agent_name}': {e}", exc_info=True)
            raise

def _get_initialized_host_agent_sync():
    
    async def _async_main():
        # Hardcode las URLs de los agentes amigos para este ejemplo
        friend_agent_urls = [
            "http://localhost:10002", # Tata Agent
            "http://localhost:10003", # Bruno Agent
            "http://localhost:10004", # Nico Agent
        ]

        logger.info("--- INICIO DEL PROGRAMA ---")
        logger.info(f"Inicializando Agente Host con {len(friend_agent_urls)} URLs de amigos.")

        # Es el responsable de manejar la comunicación con los agentes remotos
        hosting_agent_instance = await HostAgent.create(
            remote_agent_addresses = friend_agent_urls
        )

        logger.info("Agente Host totalmente inicializado y listo.")
        return hosting_agent_instance.create_agent()
        
    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            logger.warning(
                f"Advertencia: No se pudo inicializar HostAgent con `asyncio.run()`: {e}. "
                "Esto es normal en entornos como Jupyter o si ya existe un loop."
            )
        else:
            logger.critical("Error crítico al ejecutar `_async_main`", exc_info=True)
            raise

root_agent = _get_initialized_host_agent_sync()