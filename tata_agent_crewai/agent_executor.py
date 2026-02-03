import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError

from agent import TataAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TataAgentExecutor(AgentExecutor):
    """ TataAgentExecutor - Executor for TataAgent. """

    def __init__(self):
        """Initialize TataAgentExecutor."""
        self.agent = TataAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the TataAgent."""
        if not context.task_id or not context.context_id:
            raise ValueError("RequestContext debe tener task_id y context_id")
        if not context.message:
            raise ValueError("RequestContext debe tener un mensaje")

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if not context.current_task:
            await updater.submit()
        await updater.start_work()

        if self._validate_request(context):
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        try:
            result = self.agent.invoke(query)
        except Exception as e:
            logger.error(f"Se produjo un error al ejecutar el agente: {e}")
            raise ServerError(error=InternalError()) from e

        parts = [Part(root=TextPart(text=result))]

        await updater.add_artifact(parts)
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError("TataAgentExecutor no admite la ejecución."))
    
    def _validate_request(self, context: RequestContext) -> bool:
        return False


