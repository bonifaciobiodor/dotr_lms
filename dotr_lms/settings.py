"""
DOTR-LMS Django Settings
Department of Transportation – Learning Management System
"""

from pathlib import Path
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ─────────────────────────────────────────────────────────────────
# CRITICAL: set SECRET_KEY in the environment; never commit a real key to source
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'dotr-lms-insecure-dev-key-replace-before-production'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,192.168.3.108,192.168.5.93,192.168.1.2'
).split(',')

# ── Production startup guards ─────────────────────────────────────────────────
# Fail fast at startup when required production config is missing.
_is_manage = 'manage.py' in sys.argv[0] if sys.argv else False
_safe_commands = {'migrate', 'collectstatic', 'shell', 'createsuperuser', 'seed_data', 'apply_retention'}
_running_server = not (_is_manage and sys.argv[1:2] and sys.argv[1] in _safe_commands)

if not DEBUG and _running_server:
    if SECRET_KEY == 'dotr-lms-insecure-dev-key-replace-before-production':
        raise RuntimeError('DJANGO_SECRET_KEY must be set in production. Set it via environment variable.')
    if not os.environ.get('HRIS_TOKEN'):
        raise RuntimeError('HRIS_TOKEN must be set in production. Set it via environment variable.')

# ── Installed Apps ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'axes',
    'apps.accounts.apps.AccountsConfig',
    'apps.competencies.apps.CompetenciesConfig',
    'apps.trainings.apps.TrainingsConfig',
    'apps.assessments.apps.AssessmentsConfig',
    'apps.certificates.apps.CertificatesConfig',
    'apps.reports.apps.ReportsConfig',
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dotr_lms.middleware.ContentSecurityPolicyMiddleware',
]

ROOT_URLCONF = 'dotr_lms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'dotr_lms.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'accounts.User'

# ── Password validation ───────────────────────────────────────────────────────
# Complies with DICT password policy and RA 10173 data security requirements.
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'apps.accounts.validators.ComplexPasswordValidator'},
]

# ── Data Retention Schedule (RA 10173 / CSC / COA guidelines) ────────────────
# Values are in days. Management command `apply_retention` enforces these.
DATA_RETENTION = {
    # Audit/access logs — COA requires 3-year government record retention
    'AUDIT_LOG_DAYS': 3 * 365,
    # Training completion records — CSC PRIME-HRM requires 5-year retention
    'TRAINING_RECORD_DAYS': 5 * 365,
    # Assessment attempts (non-passing, no certificate) — 1 year
    'ASSESSMENT_ATTEMPT_DAYS': 1 * 365,
    # Completed erasure requests — kept for 1 year for NPC compliance proof
    'ERASURE_REQUEST_DAYS': 1 * 365,
}

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# ── Static / Media ────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Auth URLs ─────────────────────────────────────────────────────────────────
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ── Authentication backends ───────────────────────────────────────────────────
# AxesStandaloneBackend must be last so axes can reject locked-out users
# before any real credential check occurs.
AUTHENTICATION_BACKENDS = [
    'apps.accounts.backends.ExternalAPIBackend',
    'axes.backends.AxesStandaloneBackend',
]

# ── External HRIS API ─────────────────────────────────────────────────────────
# CRITICAL: set HRIS_TOKEN in the environment; never commit a real token to source
HRIS_URL = os.environ.get('HRIS_URL', 'https://prot1.dotr.gov.ph/api')
HRIS_TOKEN = os.environ.get('HRIS_TOKEN', '')

# ── Session security ──────────────────────────────────────────────────────────
SESSION_COOKIE_AGE = 28800          # 8 hours
SESSION_COOKIE_HTTPONLY = True      # JS cannot read session cookie
SESSION_COOKIE_SAMESITE = 'Lax'    # CSRF mitigation

# ── CSRF security ─────────────────────────────────────────────────────────────
CSRF_COOKIE_HTTPONLY = False        # Must be False so JS can read for AJAX
CSRF_COOKIE_SAMESITE = 'Lax'

# ── HTTPS / production hardening (activated when DEBUG=False) ─────────────────
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000      # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ── Click-jacking protection (X-Frame-Options) ────────────────────────────────
X_FRAME_OPTIONS = 'SAMEORIGIN'

# ── File upload limits ────────────────────────────────────────────────────────
# Files above 2.5 MB are written to a temp file instead of buffered in RAM,
# preventing memory exhaustion on large video uploads.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024     # 10 MB for non-file form fields
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024 + 512 * 1024  # 2.5 MB buffer threshold

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── django-axes: brute-force login protection ─────────────────────────────────
AXES_FAILURE_LIMIT = 5              # lock out after 5 consecutive failures
AXES_COOLOFF_TIME = 0.5             # lockout duration: 30 minutes (in hours)
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']  # lock both username and IP
AXES_RESET_ON_SUCCESS = True        # clear failure count on successful login
AXES_VERBOSE = False                # suppress per-request debug output
AXES_HANDLER = 'axes.handlers.database.AxesDatabaseHandler'

# ── Content Security Policy (django-csp) ──────────────────────────────────────
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ("'self'",),
        'script-src': (
            "'self'",
            'cdn.jsdelivr.net',        # Bootstrap JS, FullCalendar
            'cdnjs.cloudflare.com',    # jQuery / other CDN libs
            "'unsafe-inline'",         # inline scripts in templates (tighten later with nonces)
        ),
        'style-src': (
            "'self'",
            'cdn.jsdelivr.net',
            'cdnjs.cloudflare.com',
            'fonts.googleapis.com',
            "'unsafe-inline'",         # inline styles (Bootstrap utilities)
        ),
        'font-src': ("'self'", 'fonts.gstatic.com', 'cdn.jsdelivr.net', 'cdnjs.cloudflare.com'),
        'img-src': ("'self'", 'data:'),
        'connect-src': ("'self'",),
        'frame-ancestors': ("'self'",),
        'form-action': ("'self'",),
        'base-uri': ("'self'",),
        'object-src': ("'none'",),
    },
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'axes': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
