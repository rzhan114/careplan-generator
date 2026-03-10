import os

SECRET_KEY = "dev-secret-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "corsheaders",
    "careplan",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
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