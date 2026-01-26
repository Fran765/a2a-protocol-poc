
import random
from datetime import date, timedelta


def generate_bruno_calendar() -> dict[str, list[str]]:
    """Generates a random calendar for Bruno for the next 7 days."""
    calendar = {}
    today = date.today()
    # Disponibilidad de Bruno: Disponible durante la tarde y noche
    possible_times = [f"{h:02}:00" for h in range(14, 22)]

    for i in range(7):
        current_date = today + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")

        # Selecciona 6 horarios únicos al azar, los ordena y los asigna a la fecha correspondiente
        available_slots = sorted(random.sample(possible_times, 6))
        calendar[date_str] = available_slots

    return calendar


BRUNO_CALENDAR = generate_bruno_calendar()