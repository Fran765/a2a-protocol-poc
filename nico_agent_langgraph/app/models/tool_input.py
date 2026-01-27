from pydantic import BaseModel, Field

class AvailabilityToolInput(BaseModel):
    """Input scheme for the tool."""
    date_range: str = Field(
        ..., 
        description=("La fecha o rango de fechas para verificar la disponibilidad, e.g.,"
                     " '2025-10-01' o '2025-10-01 a 2025-10-03'."
        )
    )
