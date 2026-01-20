from datetime import datetime, timedelta
from langchain_core.tools import tool
from schemas import AvailabilityToolInput
from utils import NICO_CALENDAR

@tool(args_schema=AvailabilityToolInput)
def get_availability(date_range: str) -> str:
    """Use this tool to returns Nico's availability for a specific date or date range."""

    dates_to_check = [d.strip() for d in date_range.split("to")]
    start_date_str = dates_to_check[0]
    end_date_str = dates_to_check[-1] 

    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        if start > end:
            return "El rango de fechas no es válido. La fecha de inicio es posterior a la fecha de fin."
        
        results = []
        delta = end - start
        for i in range(delta.days + 1):
            day = start + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            available_slots = NICO_CALENDAR.get(day_str, [])
            if available_slots:
                availability = (
                    f"El {day_str}, Nico está disponible en los siguientes horarios: "
                    + ", ".join(available_slots)
                )
                results.append(availability)
            else:
                results.append(f"El {day_str}, Nico no tiene disponibilidad.")
        
        return "\n".join(results)
    
    except ValueError:
        return "El formato de fecha no es válido. Por favor, use 'YYYY-MM-DD'"