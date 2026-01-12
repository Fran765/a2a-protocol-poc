from datetime import date, datetime, timedelta
from typing import Dict

# Base de datos en memoria para los horarios.
# Mapea una fecha (string) a un diccionario de {hora: nombre_reserva}.
COURT_SCHEDULE: Dict[str, Dict[str, str]] = {}


def generate_court_schedule():
    """Generates a schedule for the basketball court for the next 7 days."""
    # Rellena COURT_SCHEDULE con horarios de 13 PM a 23 PM para los próximos 7 días.
    global COURT_SCHEDULE
    today = date.today()
    possible_times = [f"{h:02}:00" for h in range(13, 24)]  # 13 PM to 23 PM

    for i in range(7):
        current_date = today + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        # Inicializa cada horario con el valor "unknown" (disponible)
        COURT_SCHEDULE[date_str] = {time: "unknown" for time in possible_times}


# Inicializa la agenda automáticamente al importar este módulo
generate_court_schedule()


def list_court_availabilities(date: str) -> dict:
    """
    Lists the available and booked time slots for a basketball court on a given date.

    Args:
        date: The date to check, in YYYY-MM-DD format.

    Returns:
        A dictionary with the status and the detailed schedule for the day.
    """
    # Validación: Intenta convertir el string de fecha a objeto fecha sino devuelve error
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {
            "status": "error",
            "message": "Invalid date format. Please use YYYY-MM-DD.",
        }

    # Busca la fecha en la base de datos global
    daily_schedule = COURT_SCHEDULE.get(date)

    # Si la fecha no existe (ej. es una fecha fuera del rango de 7 días)
    if not daily_schedule:
        return {
            "status": "success",
            "message": f"The court is not open on {date}.",
            "schedule": {},
        }

    # Filtra los horarios donde el valor es "unknown" (Libres)
    available_slots = [
        time for time, party in daily_schedule.items() if party == "unknown"
    ]

    # Filtra los horarios donde el valor NO es "unknown" (Ocupados)
    booked_slots = {
        time: party for time, party in daily_schedule.items() if party != "unknown"
    }

    # Retorna el resumen del día
    return {
        "status": "success",
        "message": f"Schedule for {date}.",
        "available_slots": available_slots,
        "booked_slots": booked_slots,
    }


def book_basketball_court(
    date: str, start_time: str, end_time: str, reservation_name: str
) -> dict:
    """
    Books a basketball court for a given date and time range under a reservation name.
    Args:
        date: The date of the reservation, in YYYY-MM-DD format.
        start_time: The start time of the reservation, in HH:MM format.
        end_time: The end time of the reservation, in HH:MM format.
        reservation_name: The name for the reservation.

    Returns:
        A dictionary confirming the booking or providing an error.
    """
    # Validación: Verifica que fecha y horas tengan el formato correcto sino devuelve error
    try:
        start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return {
            "status": "error",
            "message": "Invalid date or time format. Please use YYYY-MM-DD and HH:MM.",
        }

    # La hora de inicio no puede ser mayor o igual al fin
    if start_dt >= end_dt:
        return {"status": "error", "message": "Start time must be before end time."}

    # Verifica si la fecha está habilitada en la agenda
    if date not in COURT_SCHEDULE:
        return {"status": "error", "message": f"The court is not open on {date}."}

    # Obliga a que la reserva tenga un nombre asociado
    if not reservation_name:
        return {
            "status": "error",
            "message": "Cannot book a court without a reservation name.",
        }

    # ==============================================================================
    # FUNCIONAMIENTO DE LOS SLOTS
    # ==============================================================================
    # El usuario puede pedir un rango continuo (ej. "de 13:00 a 15:00"),
    # el sistema internamente funciona con bloques atómicos de 1 hora (slots).
    #
    # El siguiente codigo traduce el "deseo del usuario" (3 turnos) al "lenguaje del sistema"
    # (ocupando los slots de las 13:00, las 14:00 y las 15:00).
    # ==============================================================================

    required_slots = []
    current_time = start_dt

    # Genera una lista con todas las horas individuales necesarias (ej. ["13:00", "14:00"])
    while current_time < end_dt:
        required_slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(hours=1)

    daily_schedule = COURT_SCHEDULE.get(date, {})

    # --- Verificación de Disponibilidad ---
    # Revisa si ALGUNO de los slots necesarios ya está ocupado
    for slot in required_slots:
        # Si el slot existe y NO es "unknown", hay conflicto
        if daily_schedule.get(slot, "booked") != "unknown":
            party = daily_schedule.get(slot)
            return {
                "status": "error",
                "message": f"The time slot {slot} on {date} is already booked by {party}.",
            }

    # --- Ejecución de la Reserva ---
    # Si llegamos aca, todos los slots están libres. Procedemos a escribir el nombre.
    for slot in required_slots:
        COURT_SCHEDULE[date][slot] = reservation_name

    return {
        "status": "success",
        "message": f"Success! The basketball court has been booked for {reservation_name} from {start_time} to {end_time} on {date}.",
    }
