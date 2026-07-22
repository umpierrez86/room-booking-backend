"""Eval cases for the room-booking agent: natural-language input -> expected tool call."""

CASES = [
    {
        "input": "Reservá la Sala C mañana de 10:00 a 11:30 para 6, título Sprint Review",
        "expected_tool": "create_booking",
        "expected_args": {"room": "C", "start": "10:00", "end": "11:30", "attendees": 6},
    },
    {
        "input": "¿Qué salas están libres mañana de 10 a 11 para 6 personas?",
        "expected_tool": "list_available_rooms",
        "expected_args": {"attendees": 6},
    },
    {
        "input": "Mostrame la agenda de la Sala D para mañana",
        "expected_tool": "get_room_schedule",
        "expected_args": {"room": "D"},
    },
    {
        "input": "Cancelá mi reserva de la Sala C",
        "expected_tool": "list_my_bookings",
        "expected_args": {},  # primero lista para hallar el id
    },
    {
        "input": "Reservá la Sala A para 30 personas mañana de 10 a 11",
        "expected_tool": "create_booking",
        "expected_args": {"room": "A"},  # el dominio rechaza por capacidad
    },
]
