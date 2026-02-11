CONTENT_ORIGIN = "https://pulp:443"
ANSIBLE_API_HOSTNAME = "https://pulp:443"
ANSIBLE_CONTENT_HOSTNAME = "https://pulp:443/pulp/content"
PRIVATE_KEY_PATH = "/etc/pulp/certs/token_private_key.pem"
PUBLIC_KEY_PATH = "/etc/pulp/certs/token_public_key.pem"
TOKEN_SERVER = "https://pulp:443/token/"
TOKEN_SIGNATURE_ALGORITHM = "ES256"
CACHE_ENABLED = True
REDIS_HOST = "localhost"
REDIS_PORT = 6379
ANALYTICS = False

API_ROOT = '/rerouted/djnd/'

ALLOWED_EXPORT_PATHS =["/tmp"]
ALLOWED_IMPORT_PATHS = ["/tmp"]
CONTENT_PATH_PREFIX = "/somewhere/else/"
CSRF_TRUSTED_ORIGINS = ["https://pulp:443"]
ORPHAN_PROTECTION_TIME = 0
TASK_PROTECTION_TIME = 10
TMPFILE_PROTECTION_TIME = 10
UPLOAD_PROTECTION_TIME = 10

DISABLED_AUTHENTICATION_BACKENDS="@merge django.contrib.auth.backends.RemoteUserBackend"
DISABLED_AUTHENTICATION_JSON_HEADER="HTTP_X_RH_IDENTITY"
DISABLED_AUTHENTICATION_JSON_HEADER_JQ_FILTER=".identity.user.username"
DISABLED_AUTHENTICATION_JSON_HEADER_OPENAPI_SECURITY_SCHEME={
    "description": "External OAuth integration",
    "flows": {
        "clientCredentials": {
            "scopes": {
                "api.console": "grant_access_to_pulp"
            },
            "tokenUrl": "https://your-identity-provider/token/issuer"
        }
    },
    "type": "oauth2"
}
DISABLED_REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES="@merge pulpcore.app.authentication.JSONHeaderRemoteAuthentication"
MEDIA_ROOT=""
STORAGES={
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": "AKIAIT2Z5TDYPX3ARJBA",
            "addressing_style": "path",
            "bucket_name": "pulp3",
            "default_acl": "@none",
            "endpoint_url": "http://minio:9000",
            "region_name": "eu-central-1",
            "secret_key": "fqRvjWaPU5o0fCqQuUWbj9Fainj2pVZtBCiDiieS",
            "signature_version": "s3v4"
        }
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    }
}
DOMAIN_ENABLED = True
HIDE_GUARDED_DISTRIBUTIONS = True
REST_FRAMEWORK__DEFAULT_PERMISSION_CLASSES = [
    "pulpcore.plugin.access_policy.AccessPolicyFromSettings"
]
SPECTACULAR_SETTINGS__OAS_VERSION = "3.0.3"
