import logging
import os
import sys
import click
import httpx
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import ( 
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore, 
    InMemoryTaskStore
)
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent import NicoAgent
from agent_executor import NicoAgentExecutor
from exceptions.apikey_exception import MissingAPIKeyError
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10004)
def main(host, port):
    """ Punto de inicio al servidor de NicoAgent. """

    try:
        if not os.getenv("GOOGLE_API_KEY"):
            raise MissingAPIKeyError("Variable de entorno (GOOGLE_API_KEY) no establecida")
        
        capabilities = AgentCapabilities(streaming=True, push_notifications=True)
        
        skills = AgentSkill(
            id = "schedule_basketball",
            name = "Basketball Scheduling Tool",
            description = "Ayuda a encontrar la disponibilidad de Nico para el baloncesto.",
            tags = ["scheduling", "basketball", "availability"],
            examples = ["¿Cuándo está Nico disponible para jugar al baloncesto la próxima semana?"],
        )

        card = AgentCard(
            name = "Agente Nico",
            description = "Un agente para gestionar la disponibilidad de Nico para jugar al baloncesto.",
            url = f"http://{host}:{port}",
            version = "1.0.0",
            default_input_modes = NicoAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes = NicoAgent.SUPPORTED_CONTENT_TYPES,
            skills = [skills],
            capabilities = capabilities,
        )

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(httpx_client = httpx_client,
                                                 config_store = push_config_store
                                                )
        
        request_handler = DefaultRequestHandler(
            agent_executor = NicoAgentExecutor(),
            task_store = InMemoryTaskStore(),
            push_config_store = push_config_store,
            push_sender = push_sender,
        )

        server = A2AStarletteApplication(
            agent_card = card,
            http_handler = request_handler,
        )

        uvicorn.run(server.build, host = host, port = port)

    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Se produjo un error durante el inicio del servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()