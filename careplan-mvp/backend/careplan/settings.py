import os

SECRET_KEY = "dev-secret-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django_prometheus',  # 加在最前面
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "corsheaders",
    "careplan",
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # 第一个
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    'django_prometheus.middleware.PrometheusAfterMiddleware',   # 最后一个
]

# 开发环境允许前端跨域访问后端
CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = "careplan.urls"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'careplan',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': '5432',
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# Redis配置
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
# 加 Celery 配置
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_TASK_SERIALIZER = 'json'
os.environ.setdefault('PROMETHEUS_MULTIPROC_DIR', '/tmp')