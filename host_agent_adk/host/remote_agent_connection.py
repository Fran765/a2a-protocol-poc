from typing import Callable

import logging
import httpx
from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    SendMessageRequest,
    SendMessageResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
from dotenv import load_dotenv

logger = logging.getLogger("RemoteConnections")

load_dotenv()

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, agent_card: AgentCard, agent_url: str):
        logger.info(f"Inicializando conexión remota con agente: '{agent_card.name}'")
        logger.debug(f"Target URL: {agent_url}")

        self._httpx_client = httpx.AsyncClient(timeout=30)

        try:
            self.agent_client = A2AClient(self._httpx_client, agent_card, url=agent_url)
            logger.debug(f"Cliente A2A instanciado correctamente para {agent_card.name}")
        except Exception as e:
            logger.error(f"Error fatal al crear A2AClient para {agent_url}: {e}")
            raise

        self.card = agent_card
        self.conversation_name = None
        self.conversation = None
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(
        self, message_request: SendMessageRequest
    ) -> SendMessageResponse:
        logger.info(f"OUTGOING: Enviando mensaje A2A a '{self.card.name}' (MsgID: {message_request.id})")
        try:
            response = await self.agent_client.send_message(message_request)
            
            logger.info(f"INCOMING: Respuesta recibida de '{self.card.name}'")
            return response
            
        except httpx.TimeoutException:
            logger.error(f"TIMEOUT: El agente '{self.card.name}' tardó demasiado en responder.")
            raise
        except Exception as e:
            logger.error(f"FALLO DE ENVÍO a '{self.card.name}': {e}", exc_info=True)
            raise