"""Django settings for the OpsPilot API project."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

DEVELOPMENT_SECRET_KEY = "django-insecure-development-only-change-me"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", DEVELOPMENT_SECRET_KEY)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

if not DEBUG and (
    SECRET_KEY == DEVELOPMENT_SECRET_KEY
    or len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be a long, random value when DJANGO_DEBUG is false."
    )

LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
    LOG_LEVEL = "INFO"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.inlines",
    "ninja",
    "apps.accounts.apps.AccountsConfig",
    "apps.operations.apps.OperationsConfig",
    "apps.conversations.apps.ConversationsConfig",
    "apps.audit.apps.AuditConfig",
    "apps.knowledge.apps.KnowledgeConfig",
    "apps.agents.apps.AgentsConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "config.middleware.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "config.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "opspilot": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "opspilot"),
        "USER": os.environ.get("POSTGRES_USER", "opspilot"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.environ.get("POSTGRES_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "accounts.User"

SECURE_COOKIES = os.environ.get(
    "DJANGO_SECURE_COOKIES",
    str(not DEBUG),
).lower() == "true"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = SECURE_COOKIES
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SAMESITE = "Lax"

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Dokploy terminates TLS at Traefik and forwards the original scheme. Django
# still owns HTTPS redirects and secure-cookie behavior for defense in depth.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = os.environ.get(
    "DJANGO_SECURE_SSL_REDIRECT",
    str(not DEBUG),
).lower() == "true"
SECURE_HSTS_SECONDS = int(
    os.environ.get("DJANGO_HSTS_SECONDS", "3600" if not DEBUG else "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get(
    "DJANGO_HSTS_INCLUDE_SUBDOMAINS", "false"
).lower() == "true"
SECURE_HSTS_PRELOAD = os.environ.get(
    "DJANGO_HSTS_PRELOAD", "false"
).lower() == "true"

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

# Uploaded knowledge files are private application data. No URL route serves this
# directory; authorized APIs expose metadata and citations only.
MEDIA_ROOT = Path(os.environ.get("OPSPILOT_PRIVATE_MEDIA_ROOT", BASE_DIR / "private_media"))

KNOWLEDGE_MAX_UPLOAD_BYTES = int(
    os.environ.get("KNOWLEDGE_MAX_UPLOAD_BYTES", 10 * 1024 * 1024)
)
KNOWLEDGE_MAX_PDF_PAGES = int(os.environ.get("KNOWLEDGE_MAX_PDF_PAGES", 100))
KNOWLEDGE_EMBEDDING_DIMENSION = 384
KNOWLEDGE_EMBEDDING_PROVIDER = os.environ.get(
    "KNOWLEDGE_EMBEDDING_PROVIDER", "local_hashing_v1"
)
KNOWLEDGE_MIN_SIMILARITY = float(
    os.environ.get("KNOWLEDGE_MIN_SIMILARITY", "0.15")
)

# P3 agent limits are enforced in application code, outside model instructions.
OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-6-luna")
OPENAI_MAX_OUTPUT_TOKENS = min(
    max(int(os.environ.get("OPENAI_MAX_OUTPUT_TOKENS", "800")), 128),
    2_000,
)
AGENT_MAX_LLM_CALLS = min(
    max(int(os.environ.get("AGENT_MAX_LLM_CALLS", "4")), 1),
    6,
)
AGENT_MAX_TOOL_CALLS = min(
    max(int(os.environ.get("AGENT_MAX_TOOL_CALLS", "3")), 1),
    5,
)
AGENT_REQUEST_TIMEOUT_SECONDS = min(
    max(float(os.environ.get("AGENT_REQUEST_TIMEOUT_SECONDS", "30")), 5.0),
    60.0,
)
AGENT_MAX_TOTAL_TOKENS = min(
    max(int(os.environ.get("AGENT_MAX_TOTAL_TOKENS", "12000")), 512),
    50_000,
)
AGENT_MAX_CONCURRENT_RUNS = min(
    max(int(os.environ.get("AGENT_MAX_CONCURRENT_RUNS", "2")), 1),
    5,
)
AGENT_RATE_LIMIT_REQUESTS = min(
    max(int(os.environ.get("AGENT_RATE_LIMIT_REQUESTS", "20")), 1),
    100,
)
AGENT_RATE_LIMIT_WINDOW_SECONDS = min(
    max(int(os.environ.get("AGENT_RATE_LIMIT_WINDOW_SECONDS", "3600")), 60),
    86_400,
)
AGENT_USER_TOKEN_BUDGET = min(
    max(int(os.environ.get("AGENT_USER_TOKEN_BUDGET", "100000")), 1_000),
    10_000_000,
)
AGENT_TOKEN_BUDGET_WINDOW_SECONDS = min(
    max(int(os.environ.get("AGENT_TOKEN_BUDGET_WINDOW_SECONDS", "86400")), 60),
    2_592_000,
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    "redis://localhost:6379/0",
)

CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    "redis://localhost:6379/1",
)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_SOFT_TIME_LIMIT = 110
CELERY_TASK_TIME_LIMIT = 120

CRISPY_ALLOWED_TEMPLATE_PACKS = ["unfold_crispy"]

CRISPY_TEMPLATE_PACK = "unfold_crispy"

UNFOLD = {
    "SITE_TITLE": "OpsPilot administration",
    "SITE_HEADER": "OpsPilot",
    "SITE_SUBHEADER": "Operations administration",
    "SITE_SYMBOL": "support_agent",
}
