import logging
import os
import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent import create_agent
from agent_executor import BrunoAgentExecutor
from exceptions.apikey_exception import MissingAPIKeyError
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10003)
def main(host, port):
    """ Punto de inicio al servidor de BrunoAgent."""

    try:
        if not os.getenv("GOOGLE_API_KEY"):
            raise MissingAPIKeyError("La variable de entorno GOOGLE_API_KEY no esta iniciada.")

        capabilities = AgentCapabilities(streaming=True)

        skill = AgentSkill(
            id = "schedule_basketball",
            name = "Basketball Scheduling Tool",
            description = "Ayuda a encontrar la disponibilidad de Bruno para jugar al baloncesto.",
            tags = ["scheduling", "basketball", "availability"],
            examples= ["Bruno esta libre mañana para jugar al baloncesto?"]
        )

        card = AgentCard(
            name = "Agente Bruno",
            description = "Un agente para gestionar la disponibilidad de Bruno para jugar al baloncesto.",
            url = f"http://{host}:{port}",
            version = "1.0.0",
            default_input_modes = ["text/plain"],
            default_output_modes = ["text/plain"],
            skills = [skill],
            capabilities = capabilities,
        )

        agent = create_agent()

        runner = Runner(
            app_name = card.name,
            agent = agent,
            artifact_service= InMemoryArtifactService(),
            session_service= InMemorySessionService(),
            memory_service= InMemoryMemoryService(),
        )

        agent_executor = BrunoAgentExecutor(runner)

        request_handler = DefaultRequestHandler(
            agent_executor = agent_executor,
            task_store = InMemoryTaskStore()
        )

        server = A2AStarletteApplication(
            agent_card = card,
            http_handler = request_handler,
        )

        uvicorn.run(server.build, host = host, port = port)

    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Se produjo un error durante el inicio del servidor: {e}")
        exit(1)


if __name__ == "__main__":
    main()