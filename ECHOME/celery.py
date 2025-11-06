import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ECHOME.settings')

app = Celery('ECHOME')

# Load settings from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks.py from each app
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
