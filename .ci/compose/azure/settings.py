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

ALLOWED_EXPORT_PATHS =["/tmp"]
ALLOWED_IMPORT_PATHS = ["/tmp"]
CONTENT_PATH_PREFIX = "/somewhere/else/"
CSRF_TRUSTED_ORIGINS = ["https://pulp:443"]
ORPHAN_PROTECTION_TIME = 0
TASK_PROTECTION_TIME = 10
TMPFILE_PROTECTION_TIME = 10
UPLOAD_PROTECTION_TIME = 10

MEDIA_ROOT = ''
STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.azure_storage.AzureStorage',
        'OPTIONS': {
            'account_key': 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==',
            'account_name': 'devstoreaccount1',
            'azure_container': 'pulp-test',
            'connection_string': 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://ci-azurite:10000/devstoreaccount1;',
            'expiration_secs': 120,
            'location': 'pulp3',
            'overwrite_files': True,
        },
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
API_ROOT_REWRITE_HEADER = "X-API-Root"
CONTENT_ORIGIN = None
DOMAIN_ENABLED = True
REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES = '@merge pulpcore.app.authentication.PulpRemoteUserAuthentication'
REST_FRAMEWORK__DEFAULT_PERMISSION_CLASSES = ['pulpcore.plugin.access_policy.DefaultAccessPolicy']
TASK_DIAGNOSTICS = ['memory']
