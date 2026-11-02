"""Monitores de Sentry para las tareas programadas (Developer Pack: Sentry).

Con ``SENTRY_DSN`` en el entorno, cada tarea avisa a Sentry cuando empieza y cuando termina
(Crons). Si una tarea semanal deja de reportar o falla, Sentry manda el aviso. Sin la variable,
o sin el paquete ``sentry-sdk``, no hace nada: la tarea corre igual.
"""
import contextlib
import os

# Horario de cada monitor, igual al cron de su tarea en .github/workflows/.
HORARIOS = {
    "g7b-opendata": "23 8 * * 1",
    "g7b-cubo": "53 8 * * 1",
    "g7b-sonda-matriz": "11 7 * * 2",
}


@contextlib.contextmanager
def monitor(nombre):
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        yield
        return
    try:
        import sentry_sdk
        from sentry_sdk.crons import monitor as monitor_sentry
    except ImportError:
        yield
        return
    sentry_sdk.init(dsn=dsn, traces_sample_rate=0, send_default_pii=False,
                    environment=os.environ.get("SENTRY_ENTORNO", "produccion"))
    configuracion = {"schedule": {"type": "crontab", "value": HORARIOS.get(nombre, "0 0 * * *")},
                     "checkin_margin": 60, "max_runtime": 120, "timezone": "UTC"}
    with monitor_sentry(monitor_slug=nombre, monitor_config=configuracion):
        yield
    sentry_sdk.flush(timeout=10)
