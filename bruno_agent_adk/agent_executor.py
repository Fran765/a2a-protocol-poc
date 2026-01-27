import logging
from collections.abc import AsyncGenerator

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState, UnsupportedOperationError
from a2a.utils.errors import ServerError
from google.adk import Runner
from google.adk.events import Event
from google.genai import types

from helpers.parts_converters import (
    convert_a2a_parts_to_genai,
    convert_genai_parts_to_a2a,
)

logger = logging.getLogger("BrunoExecutor")
logger.setLevel(logging.DEBUG)

class BrunoAgentExecutor(AgentExecutor):
    """AgentExecutor that runs the Bruno ADK-based agent."""

    def __init__(self, runner: Runner):
        self.runner = runner
        self._running_sessions = {}
        logger.info("BrunoAgentExecutor inicializado.")

    def _run_agent(
            self, session_id, new_message: types.Content
    ) -> AsyncGenerator[Event, None]:
        logger.debug(f"Ejecutando runner para sesión: {session_id}")
        return self.runner.run_async(
            session_id=session_id, user_id="bruno_agent", new_message=new_message
            )
    
    async def _process_request(
            self,
            new_message: types.Content,
            session_id: str,
            task_updater: TaskUpdater
    ) -> None:
        
        logger.info(f"Procesando solicitud para sesión {session_id}")

        session_obj = await self._upsert_session(session_id)
        session_id = session_obj.id

        logger.debug(f"Sesión activa confirmada: {session_id}")

        async for event in self._run_agent(session_id, new_message):
            if event.is_final_response():
                parts = convert_genai_parts_to_a2a(
                    event.content.parts if event.content and event.content.parts else []
                    )
                logger.debug("Dando respuesta final: %s", parts)
                
                await task_updater.add_artifact(parts)
                await task_updater.complete()

                logger.info("Tarea completada y artefactos enviados.")
                break

            if not event.get_function_calls():
                logger.debug("Enviando actualización de estado (WORKING)...")

                await task_updater.update_status(
                    TaskState.working,
                    message = task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(
                            event.content.parts if event.content and event.content.parts else []
                        ),
                    ),
                )
            else:
                logger.debug("Evento con llamada a función ignorado")

    async def execute(
            self, 
            context: RequestContext, 
            event_queue: EventQueue
    ):
        logger.info(f"EXECUTE START: TaskID={context.task_id} | ContextID={context.context_id}")

        if not context.task_id or not context.context_id:
            logger.error("Error: Faltan IDs en el contexto")
            raise ServerError("Faltan task_id o context_id en el contexto de la solicitud.")
        
        if not context.message:
            logger.error("Error: Mensaje vacío en el contexto")
            raise ServerError("Falta el mensaje en el contexto de la solicitud.")
        
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        if not context.current_task:
            logger.debug("Enviando evento SUBMIT (Nueva tarea)")
            await updater.submit()

        logger.debug("Enviando evento START_WORK")
        await updater.start_work()
        
        try:
            await self._process_request(
                types.UserContent(
                    parts=convert_a2a_parts_to_genai(context.message.parts),
                ),
                context.context_id,
                updater,
            )
        except Exception as e:
            logger.error(f"Excepción durante _process_request: {e}", exc_info=True)
            raise

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        logger.warning(f"Intento de cancelación no soportado para TaskID: {context.task_id}")
        raise ServerError(error=UnsupportedOperationError())

    async def _upsert_session(self, session_id: str):
        # Intenta obtener la sesión existente o crear una nueva si no existe
        logger.debug(f"Buscando sesión existente: {session_id}")

        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id="bruno_agent", session_id=session_id
        )

        if session:
            logger.info(f"Sesión existente recuperada: {session_id}")
        else:
            logger.info(f"Sesión no encontrada. Creando nueva sesión: {session_id}")
            session = await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id="bruno_agent",
                session_id=session_id,
            )

        if session is None:
            logger.critical(f"FALLO CRÍTICO: No se pudo obtener ni crear la sesión {session_id}")
            raise RuntimeError(f"No se pudo obtener o crear la sesión: {session_id}")
        return session
