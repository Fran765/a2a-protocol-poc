from pydantic import BaseModel, Field

class AvailabilityToolInput(BaseModel):
    """Input schema for AvailabilityTool."""

    date_range: str = Field(
        ...,
        description="La fecha o rango de fechas para verificar la disponibilidad, e.g., '2024-07-28' o '2024-07-28 to 2024-07-30'.",
    )