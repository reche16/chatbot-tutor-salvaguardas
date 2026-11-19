"""Worker (Seção 4.3.1): regrava interações pendentes e anonimiza (RN05, RN08)."""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("tutor")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "reprocessar-interacoes": {"task": "atendimento.tasks.reprocessar_interacoes", "schedule": 60.0},
    "anonimizar-mensal": {"task": "atendimento.tasks.anonimizar_interacoes", "schedule": crontab(0, 3, day_of_month=1)},
}
