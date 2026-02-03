import click
import logging
import os

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv

from agent import TataAgent
from agent_executor import TataAgentExecutor

load_dotenv()

class MissingAPIKeyError(Exception):
    """Exception for missing API key."""

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10002)
def main(host, port):
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("Variable de entorno 'GOOGLE_API_KEY' no establecida.")
        
        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="availability_checking",
            name="Availability Checking",
            description="Consulta el calendario de Tata para ver cuándo está disponible para un partido de baloncesto.",
            tags=["scheduling", "calendar", "availability"],
            examples=["¿Que horario está disponible el tata para jugar al baloncesto el sábado por la tarde?",
                      "Mañana esta libre el tata?"
                      ],
        )
        card = AgentCard(
            name = "Agente Tata",
            description = "Un agente que gestiona la disponibilidad de Tata para jugar al baloncesto.",
            url = f"http://{host}:{port}",
            version = "1.0.0",
            default_input_modes = TataAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes = TataAgent.SUPPORTED_CONTENT_TYPES,
            capabilities = capabilities,
            skills = [skill],
        )
        
        request_handler = DefaultRequestHandler(
            agent_executor = TataAgentExecutor(),
            task_store = InMemoryTaskStore(),
        )

        server = A2AStarletteApplication(
            agent_card = card,
            http_handler = request_handler,
        )

        uvicorn.run(server.build(), host=host, port=port)

    except MissingAPIKeyError as e:
        logging.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logging.error(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
