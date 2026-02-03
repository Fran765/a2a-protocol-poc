
import random
from datetime import date, timedelta


def generate_calendar() -> dict[str, list[str]]:
    """Generates a random calendar for the next 7 days."""
    calendar = {}
    today = date.today()
    possible_times = [f"{h:02}:00" for h in range(15, 24)]

    for i in range(7):
        current_date = today + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        available_slots = sorted(random.sample(possible_times, 8))
        calendar[date_str] = available_slots
    return calendar


TATA_CALENDAR = generate_calendar()
