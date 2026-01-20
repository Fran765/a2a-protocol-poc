import random
from datetime import date, timedelta

def generate_nico_calendar() -> dict[str, list[str]]:
    """Generate Nico calendar for the next 7 days."""
    nico_calendar = {}
    today = date.today()

    # Disponibilidad de Nico: A la tarde / noche durante la semana y mas libre los fines de semana
    for i in range(7):
        day = today + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        day_of_week = day.weekday()

        if day_of_week < 5:  # Dias laborables
            possible_times = [f"{h:02}:00" for h in range(18, 24)] 
            available_slots = sorted(random.sample(possible_times, random.randint(2, 3)))
        
        else:  # Fines de semana
            possible_times = [f"{h:02}:00" for h in range(13, 24)]
            available_slots = sorted(random.sample(possible_times, random.randint(4, 6)))
        
        nico_calendar[date_str] = available_slots
    
    return nico_calendar

# Generamos la "Base de datos" simulada
NICO_CALENDAR = generate_nico_calendar()