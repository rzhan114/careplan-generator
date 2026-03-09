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

# 数据库先不用 - Day 3 才会加上
# 所有数据存在内存里（Python 字典）

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
