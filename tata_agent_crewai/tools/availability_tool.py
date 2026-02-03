from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Type
from crewai.tools import BaseTool

from models.availability_schema import AvailabilityToolInput
from helpers.calendar_helper import TATA_CALENDAR

class AvailabilityTool(BaseTool):
    name: str = "Calendar Availability Checker"
    description: str = (
        "Comprueba la disponibilidad de TATA para una fecha o rango de fechas determinado. "
        "Utilice esto para saber cuándo el TATA esta libre."
    )
    args_schema: Type[BaseModel] = AvailabilityToolInput

    def _run(self, date_range: str) -> str:
        """Checks TATA's availability for a given date range."""
        dates_to_check = [d.strip() for d in date_range.split("to")]
        start_date_str = dates_to_check[0]
        end_date_str = dates_to_check[-1]

        try:
            start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            if start > end:
                return ("Rango de fechas no válido. La fecha de inicio no puede ser posterior a la fecha de finalización.")

            results = []
            delta = end - start
            for i in range(delta.days + 1):
                day = start + timedelta(days=i)
                date_str = day.strftime("%Y-%m-%d")
                available_slots = TATA_CALENDAR.get(date_str, [])
                if available_slots:
                    availability = f"En {date_str}, TATA está disponible a las: {', '.join(available_slots)}."
                    results.append(availability)
                else:
                    results.append(f"TATA no está disponible en {date_str}.")

            return "\n".join(results)

        except ValueError:
            return ("Formato de fecha no válido. Por favor, pregunta para verificar la disponibilidad para una fecha como 'YYYY-MM-DD'.")