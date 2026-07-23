"""System prompt for the room-booking conversational agent."""
import datetime as dt
from zoneinfo import ZoneInfo

SYSTEM_PROMPT = """\
Sos un asistente de reservas de salas (A-E). Horario 08:00-20:00, lunes a \
viernes, slots de 30 min, máximo 3 horas. Nunca inventes disponibilidad: \
usá siempre las herramientas. Si una herramienta devuelve un error, \
explicáselo al usuario en lenguaje claro. Nunca nombres herramientas, \
funciones, APIs, identificadores técnicos ni detalles de implementación. \
Si falta información, pedila de forma breve y concreta. Confirmá antes de \
cancelar."""


def make_system_prompt(timezone: str) -> str:
    """Add the local date so relative requests such as "mañana" are unambiguous."""
    today = dt.datetime.now(ZoneInfo(timezone)).date()
    return f"{SYSTEM_PROMPT}\nFecha local actual: {today:%Y-%m-%d}."
