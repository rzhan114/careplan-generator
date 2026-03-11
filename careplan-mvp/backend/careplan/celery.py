# backend/careplan/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'careplan.settings')

app = Celery('careplan')

# 从 Django settings 读配置，所有 Celery 配置以 CELERY_ 开头
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有 app 里的 tasks.py
app.autodiscover_tasks()