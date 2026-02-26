"""
Django settings for config project.

Objectifs:
- DEBUG piloté via env
- Static OK en dev et en prod (WhiteNoise)
- Templates trouvés dans:
    - core/templates/... (APP_DIRS=True)
    - templates/ à la racine projet (DIRS=[BASE_DIR/"templates"])
"""

from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================
# SECURITY
# =========================================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-anzbmd&37%gu6k!&rx@f%gjc$8gk$0=*w=d3tu=(%u(hu+d))7",
)

# ✅ DEBUG contrôlé par variable d'env (ne pas forcer en dur)
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "coursesapp.upidev.com"]
CSRF_TRUSTED_ORIGINS = ["https://coursesapp.upidev.com"]

# =========================================================
# APPS
# =========================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
   
    "core.apps.CoreConfig",
]

# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # ✅ WhiteNoise: sert les static en prod (et gère cache + compression)
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =========================================================
# URLS / WSGI
# =========================================================

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# =========================================================
# DATABASE
# =========================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT"),
        "OPTIONS": {"connect_timeout": 3},
    }
}

# =========================================================
# AUTH PASSWORD VALIDATION
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================================================
# I18N / TZ
# =========================================================

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

# =========================================================
# STATIC FILES (CSS / IMAGES / JS)
# =========================================================

STATIC_URL = "/static/"

# ✅ En prod: collectstatic copie tout ici
STATIC_ROOT = BASE_DIR / "staticfiles"

# ✅ WhiteNoise storage (cache-busting via hash)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# (Optionnel) Si tu as un dossier static/ à la racine du projet:
# STATICFILES_DIRS = [BASE_DIR / "static"]

# =========================================================
# DEFAULT AUTO FIELD
# =========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =========================================================
# AUTH / LOGIN
# =========================================================

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/"
# "django.contrib.admin",