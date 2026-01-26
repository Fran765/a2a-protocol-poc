from datetime import datetime, timedelta
from helpers.calendar_helper import BRUNO_CALENDAR

def get_availability(start_date: str, end_date: str) -> str:
    """
    Checks Bruno's availability for a given date range.

    Args:
        start_date: The start of the date range to check, in YYYY-MM-DD format.
        end_date: The end of the date range to check, in YYYY-MM-DD format.

    Returns:
        A string listing Bruno's available times for that date range.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start > end:
            return "Rango de fechas no válido. La fecha de inicio no puede ser posterior a la fecha de finalización."

        results = []
        delta = end - start
        for i in range(delta.days + 1):
            day = start + timedelta(days=i)
            date_str = day.strftime("%Y-%m-%d")
            available_slots = BRUNO_CALENDAR.get(date_str, [])
            if available_slots:
                availability = f"On {date_str}, Bruno is available on: {', '.join(available_slots)}."
                results.append(availability)
            else:
                results.append(f"Bruno is not available on {date_str}.")

        return "\n".join(results)

    except ValueError:
        return ("Formato de fecha no válido. Utilice AAAA-MM-DD para las fechas de inicio y fin.")