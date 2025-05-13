"""
Django settings for ciso_assistant project.

CORS are not managed by backend, so CORS library is not used

if "POSTGRES_NAME" environment variable defined, the database engine is posgresql
and the other env variables are POSTGRES_USER, POSTGRES_PASSWORD, DB_HOST, DB_PORT
else it is sqlite, and no env variable is required

"""

from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta
import logging.config
import structlog
from django.core.management.utils import get_random_secret_key
from ciso_assistant import meta

BASE_DIR = Path(os.getenv("DJANGO_BASE_DIR", Path(__file__).resolve().parent.parent))

load_dotenv(BASE_DIR / ".meta")

VERSION = os.getenv("CISO_ASSISTANT_VERSION", "unset")
BUILD = os.getenv("CISO_ASSISTANT_BUILD", "unset")
SCHEMA_VERSION = meta.SCHEMA_VERSION

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = os.environ.get("LOG_FORMAT", "plain")
LOG_OUTFILE = os.environ.get("LOG_OUTFILE", "")

CISO_ASSISTANT_URL = os.environ.get("CISO_ASSISTANT_URL", "http://localhost:5173")


def set_ciso_assistant_url(_, __, event_dict):
    event_dict["ciso_assistant_url"] = CISO_ASSISTANT_URL
    return event_dict


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
        "plain": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": LOG_FORMAT,
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": LOG_LEVEL},
    },
}

if LOG_OUTFILE:
    LOGGING["handlers"]["file"] = {
        "level": LOG_LEVEL,
        "class": "logging.handlers.WatchedFileHandler",
        "filename": "ciso-assistant.log",
        "formatter": "json",
    }
    LOGGING["loggers"][""]["handlers"].append("file")


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        set_ciso_assistant_url,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),  # ISO 8601 timestamps
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Include stack information in log entries
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.config.dictConfig(LOGGING)
logger = structlog.getLogger(__name__)

FEATURE_FLAGS = {}
MODULE_PATHS = {"serializers": "enterprise_core.serializers"}
ROUTES = {}
MODULES = {}

logger.info("Launching CISO Assistant Enterprise")

logger.info("BASE_DIR: %s", BASE_DIR)
logger.info("VERSION: %s", VERSION)
logger.info("BUILD: %s", BUILD)
logger.info("SCHEMA_VERSION: %s", SCHEMA_VERSION)

# TODO: multiple paths are explicit, it should use path join to be more generic

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
MAIL_DEBUG = os.environ.get("MAIL_DEBUG", "False") == "True"

logger.info("DEBUG mode: %s", DEBUG)
logger.info("CISO_ASSISTANT_URL: %s", CISO_ASSISTANT_URL)
# ALLOWED_HOSTS should contain the backend address
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
logger.info("ALLOWED_HOSTS: %s", ALLOWED_HOSTS)
CSRF_TRUSTED_ORIGINS = [CISO_ASSISTANT_URL]
LOCAL_STORAGE_DIRECTORY = os.environ.get(
    "LOCAL_STORAGE_DIRECTORY", BASE_DIR / "db/attachments"
)
ATTACHMENT_MAX_SIZE_MB = os.environ.get("ATTACHMENT_MAX_SIZE_MB", 10)

USE_S3 = os.getenv("USE_S3", "False") == "True"

if USE_S3:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv(
        "AWS_STORAGE_BUCKET_NAME", "ciso-assistant-bucket"
    )
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")

    if not AWS_ACCESS_KEY_ID:
        logger.error("AWS_ACCESS_KEY_ID must be set")
    if not AWS_SECRET_ACCESS_KEY:
        logger.error("AWS_SECRET_ACCESS_KEY must be set")
    if not AWS_S3_ENDPOINT_URL:
        logger.error("AWS_S3_ENDPOINT_URL must be set")
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY or not AWS_S3_ENDPOINT_URL:
        exit(1)

    logger.info("AWS_STORAGE_BUCKET_NAME: %s", AWS_STORAGE_BUCKET_NAME)
    logger.info("AWS_S3_ENDPOINT_URL: %s", AWS_S3_ENDPOINT_URL)

    AWS_S3_FILE_OVERWRITE = False

else:
    MEDIA_ROOT = LOCAL_STORAGE_DIRECTORY
    MEDIA_URL = ""

PAGINATE_BY = int(os.environ.get("PAGINATE_BY", default=5000))

# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.forms",
    "django_structlog",
    "tailwind",
    "iam",
    "global_settings",
    "tprm",
    "ebios_rm",
    "privacy",
    "resilience",
    "core",
    "cal",
    "django_filters",
    "library",
    "serdes",
    "rest_framework",
    "knox",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.saml",
    "allauth.mfa",
    "huey.contrib.djhuey",
    "auditlog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    "core.custom_middleware.AuditlogMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "ciso_assistant.urls"
# we leave these for the API UI tools - even if Django templates and Admin are not used anymore
LOGIN_REDIRECT_URL = "/api"
LOGOUT_REDIRECT_URL = "/api"

AUTH_TOKEN_TTL = int(
    os.environ.get("AUTH_TOKEN_TTL", default=60 * 60)
)  # defaults to 60 minutes
AUTH_TOKEN_AUTO_REFRESH = (
    os.environ.get("AUTH_TOKEN_AUTO_REFRESH", default="True") == "True"
)  # prevents token from expiring while user is active
AUTH_TOKEN_AUTO_REFRESH_MAX_TTL = (
    int(os.environ.get("AUTH_TOKEN_AUTO_REFRESH_MAX_TTL", default=60 * 60 * 10)) or None
)  # absolute timeout for auto-refresh, defaults to 10 hours. token expires after this time even if the user is active.

CISO_ASSISTANT_SUPERUSER_EMAIL = os.environ.get("CISO_ASSISTANT_SUPERUSER_EMAIL")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL")

EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False") == "True"
# rescue mail
EMAIL_HOST_RESCUE = os.environ.get("EMAIL_HOST_RESCUE")
EMAIL_PORT_RESCUE = os.environ.get("EMAIL_PORT_RESCUE")
EMAIL_HOST_USER_RESCUE = os.environ.get("EMAIL_HOST_USER_RESCUE")
EMAIL_HOST_PASSWORD_RESCUE = os.environ.get("EMAIL_HOST_PASSWORD_RESCUE")
EMAIL_USE_TLS_RESCUE = os.environ.get("EMAIL_USE_TLS_RESCUE", "False") == "True"

EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", default="5"))  # seconds

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "knox.auth.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "core.permissions.RBACPermissions",
        "enterprise_core.permissions.LicensePermission",
    ],
    "DEFAULT_FILTER_CLASSES": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": PAGINATE_BY,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.helpers.handle",
}

REST_KNOX = {
    "SECURE_HASH_ALGORITHM": "hashlib.sha512",
    "AUTH_TOKEN_CHARACTER_LENGTH": 64,
    "TOKEN_TTL": timedelta(seconds=AUTH_TOKEN_TTL),
    "TOKEN_LIMIT_PER_USER": None,
    "AUTO_REFRESH": AUTH_TOKEN_AUTO_REFRESH,
    "AUTO_REFRESH_MAX_TTL": timedelta(seconds=(AUTH_TOKEN_AUTO_REFRESH_MAX_TTL or 0))
    or None,
    "MIN_REFRESH_INTERVAL": 60,
}

# Empty outside of debug mode so that allauth middleware does not raise an error
STATIC_URL = ""

if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )
    # Add session authentication to allow using the browsable API
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"].append(
        "rest_framework.authentication.SessionAuthentication"
    )

    INSTALLED_APPS.append("django.contrib.staticfiles")
    STATIC_URL = "/static/"
    STATIC_ROOT = BASE_DIR / "static"

    INTERNAL_IPS = [
        "127.0.0.1",
    ]

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

WSGI_APPLICATION = "ciso_assistant.wsgi.application"

AUTH_USER_MODEL = "iam.User"

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("fr", "French"),
    ("es", "Spanish"),
    ("de", "German"),
    ("it", "Italian"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("pt", "Portuguese"),
    ("ar", "Arabic"),
    ("ro", "Romanian"),
    ("hi", "Hindi"),
    ("ur", "Urdu"),
    ("cs", "Czech"),
    ("sv", "Swedish"),
    ("id", "Indonesian"),
    ("da", "Danish"),
    ("hu", "Hungarian"),
]

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

LOCALE_PATHS = (os.path.join(PROJECT_PATH, "../locale"),)


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# SQLIte file can be changed, useful for tests
SQLITE_FILE = os.environ.get("SQLITE_FILE", BASE_DIR / "db/ciso-assistant.sqlite3")
LIBRARIES_PATH = library_path = BASE_DIR / "library/libraries"

if "POSTGRES_NAME" in os.environ:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": os.environ["POSTGRES_NAME"],
            "USER": os.environ["POSTGRES_USER"],
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ["DB_HOST"],
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": os.environ.get("CONN_MAX_AGE", 300),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": SQLITE_FILE,
            "OPTIONS": {
                "timeout": 120,
            },
        }
    }
    logger.info("SQLITE_FILE: %s", SQLITE_FILE)

logger.info("DATABASE ENGINE: %s", DATABASES["default"]["ENGINE"])

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

SPECTACULAR_SETTINGS = {
    "TITLE": "CISO Assistant API - Experimental",
    "DESCRIPTION": "CISO Assistant - API Documentation for automating all your GRC needs",
    "VERSION": "0.7.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # OTHER SETTINGS
}

# SSO with allauth

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"

# NOTE: The reauthentication flow has not been implemented in the frontend yet, hence the long timeout.
# It is used to reauthenticate the user when they are performing sensitive operations. E.g. enabling/disabling MFA.
ACCOUNT_REAUTHENTICATION_TIMEOUT = 24 * 60 * 60  # 24 hours

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ACCOUNT_ADAPTER = "iam.adapter.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "iam.adapter.SocialAccountAdapter"

SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

HEADLESS_ONLY = True

HEADLESS_TOKEN_STRATEGY = "iam.utils.KnoxTokenStrategy"

HEADLESS_FRONTEND_URLS = {
    "socialaccount_login_error": CISO_ASSISTANT_URL + "/login",
}

SOCIALACCOUNT_PROVIDERS = {
    "saml": {
        "EMAIL_AUTHENTICATION": True,
        "VERIFIED_EMAIL": True,
    },
}

ROUTES["client-settings"] = {
    "viewset": "enterprise_core.views.ClientSettingsViewSet",
    "basename": "client-settings",
}

MODULES["enterprise_core"] = {
    "path": "",
    "module": "enterprise_core.urls",
}

logger.info(
    "Enterprise startup information",
    feature_flags=FEATURE_FLAGS,
    module_paths=MODULE_PATHS,
)

LICENSE_SEATS = int(os.environ.get("LICENSE_SEATS", 1))
LICENSE_EXPIRATION = os.environ.get("LICENSE_EXPIRATION", "unset")

logger.info("License information", seats=LICENSE_SEATS, expiration=LICENSE_EXPIRATION)

INSTALLED_APPS.append("enterprise_core")

if MAIL_DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "noreply@ciso.assistant"


## Huey settings
HUEY_FILE_PATH = os.environ.get("HUEY_FILE_PATH", BASE_DIR / "db" / "huey.db")

HUEY = {
    "huey_class": "huey.SqliteHuey",
    "name": "ciso_assistant",
    "filename": HUEY_FILE_PATH,
    "results": True,  # would be interesting for debug
    "immediate": False,  # set to False to run in "live" mode regardless of DEBUG, otherwise it will follow
}
AUDITLOG_RETENTION_DAYS = int(os.environ.get("AUDITLOG_RETENTION_DAYS", 90))
AUDITLOG_MAX_RECORDS = int(os.environ.get("AUDITLOG_MAX_RECORDS", 50000))
