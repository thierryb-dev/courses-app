"""
Django settings for config project.

Objectifs de cette config:
- Simple en dev (DEBUG via env)
- Propre en prod (collectstatic vers STATIC_ROOT)
- Templates trouvés dans:
    - core/templates/... (APP_DIRS=True)
    - templates/ à la racine projet (DIRS=[BASE_DIR/"templates"])
- Static trouvés dans:
    - core/static/... (recommandé)
    - (optionnel) static/ à la racine projet si tu actives STATICFILES_DIRS
"""

from pathlib import Path
import os

# Optionnel mais pratique: pip install python-dotenv
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# SECURITY
# =========================================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    # ⚠️ Valeur par défaut ok en dev, mais en prod mets une vraie key via env
    "django-insecure-anzbmd&37%gu6k!&rx@f%gjc$8gk$0=*w=d3tu=(%u(hu+d))7",
)


# DEBUG = os.getenv("DJANGO_DEBUG", "1") in ("1", "True", "true", "yes", "YES")
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "coursesapp.upidev.com"]

CSRF_TRUSTED_ORIGINS = ["coursesapp.upidev.com"]

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
    "core",
]


# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        # ✅ Recommandé: templates globaux projet (optionnel)
        # Tu peux y mettre un layout global, emails, etc.
        "DIRS": [BASE_DIR / "templates"],
        # ✅ Indispensable pour trouver core/templates/core/*.html
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
# Config PostgreSQL (comme ton fichier actuel)
# En dev si tu veux SQLite, je peux aussi te donner une variante.

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
# ✅ Pour ton "super design", on recommande:
# - mettre ton CSS dans: core/static/core/css/app.css
# - et le charger dans base.html avec:
#   {% load static %}
#   <link rel="stylesheet" href="{% static 'core/css/app.css' %}">

STATIC_URL = "/static/"

# ✅ En prod: collectstatic va copier toutes les static ici
STATIC_ROOT = BASE_DIR / "staticfiles"

# Optionnel: si tu as UN DOSSIER static/ à la racine du projet (en plus de core/static)
# Décommente:
# STATICFILES_DIRS = [BASE_DIR / "static"]


# =========================================================
# DEFAULT AUTO FIELD
# =========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =========================================================
# AUTH / LOGIN
# =========================================================
# Si tu utilises l'admin pour te connecter, OK.
# Si tu fais un login custom plus tard, on changera ça.

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/"
