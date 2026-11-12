import datetime as dt
from zoneinfo import ZoneInfo

from app.models.operations import PoliticaClinica
from app.schemas.operations import ClinicPolicy

ZONE = ZoneInfo("America/Lima")


class PolicyService:
    def __init__(self, db):
        self.db = db

    def get(self):
        item = self.db.get(PoliticaClinica, 1)
        return ClinicPolicy.model_validate({key: getattr(item, key) for key in ClinicPolicy.model_fields}) if item else ClinicPolicy()

    def save(self, data):
        item = self.db.get(PoliticaClinica, 1)
        values = data.model_dump(mode="json")
        if item is None:
            self.db.add(PoliticaClinica(id=1, **values))
        else:
            for key, value in values.items():
                setattr(item, key, value)
        self.db.commit()
        return data

    def hours(self, date):
        policy = self.get()
        return next((item for item in policy.excepciones if item.fecha == date), next(item for item in policy.horarios if item.dia == date.weekday()))

    def within_hours(self, start, duration):
        local = start.astimezone(ZONE)
        hours = self.hours(local.date())
        end = local + dt.timedelta(minutes=duration)
        start_time, end_time = local.time().replace(tzinfo=None), end.time().replace(tzinfo=None)
        overlaps_break = hours.descanso_inicio is not None and start_time < hours.descanso_fin and end_time > hours.descanso_inicio
        return not hours.cerrado and local.date() == end.date() and hours.inicio <= start_time and end_time <= hours.fin and not overlaps_break
