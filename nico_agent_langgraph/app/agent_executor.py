import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError

from agent import NicoAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NicoExecutor")

class NicoAgentExecutor(AgentExecutor):
    """ NicoAgentExecutor - Executor for NicoAgent. """

    def __init__(self):
        self.agent = NicoAgent()
        logger.info("NicoAgentExecutor inicializado y listo.")

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        logger.info("--EXECUTE START--")

        if not context.task_id or not context.context_id:
            logger.error("Error de validación: Faltan IDs en el contexto.")
            raise ValueError("El RequestContext debe tener task_id y context_id")
        
        if not context.message:
            logger.error("Error de validación: Mensaje vacío.")
            raise ValueError("RequestContext debe tener un mensaje")

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        if not context.current_task:
            logger.debug("Enviando evento SUBMIT (Nueva tarea detectada)")
            await updater.submit()
        
        logger.debug("Iniciando trabajo (START_WORK)...")
        await updater.start_work()

        query = context.get_user_input()
        logger.info(f"Query recibido del usuario: '{query}'")

        try:
            logger.info("Iniciando stream de respuesta del agente Nico...")
            async for item in self.agent.stream(query, context.context_id):
                logger.debug(f"Chunk recibido del stream: {item}")

                is_task_complete = item["is_task_complete"]
                require_user_input = item["require_user_input"]
                parts = [Part(root=TextPart(text=item["content"]))]

                if not is_task_complete and not require_user_input:
                    logger.debug("Estado: WORKING (Generando tokens...)")
                    await updater.update_status(
                        TaskState.working,
                        message=updater.new_agent_message(parts),
                    )
                elif require_user_input:
                    logger.info("Estado: INPUT_REQUIRED (El agente pide información al usuario)")
                    await updater.update_status(
                        TaskState.input_required,
                        message=updater.new_agent_message(parts),
                    )
                    break
                else:
                    logger.info("Estado: COMPLETE. Enviando respuesta final")
                    await updater.add_artifact(
                        parts,
                        name="scheduling_result",
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.error(f"CRITICAL: Se produjo un error al transmitir la respuesta: {e}", exc_info=True)
            raise ServerError(error=InternalError()) from e

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.warning(f"Intento de cancelación no soportado para TaskID: {context.task_id}")
        raise ServerError(error=UnsupportedOperationError())