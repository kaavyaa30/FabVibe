import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')

app = Celery('ecommerce')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Explicitly list apps with tasks so autodiscovery never misses them
app.autodiscover_tasks(['products', 'orders'])


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
