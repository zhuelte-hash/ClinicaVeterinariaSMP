import logging
import time

from app.config import get_settings
from app.database import SessionLocal
from app.services.appointment_service import AppointmentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run() -> None:
    settings = get_settings()
    logger.info("Worker de citas iniciado; tolerancia=%s minutos", settings.appointment_tolerance_minutes)
    while True:
        db = SessionLocal()
        try:
            expired = AppointmentService(db).expire_unattended_appointments()
            if expired:
                logger.info("Citas canceladas automáticamente por inasistencia: %s", len(expired))
        except Exception:
            db.rollback()
            logger.exception("Error procesando vencimiento de citas")
        finally:
            db.close()
        time.sleep(settings.appointment_worker_interval_seconds)


if __name__ == "__main__":
    run()
