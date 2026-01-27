from typing import Literal
from pydantic import BaseModel

class ResponseFormat(BaseModel):
    """The output format for the agent's response."""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str