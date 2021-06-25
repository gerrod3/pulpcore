import asyncio
import logging

from aiohttp.web import middleware
from concurrent.futures import ThreadPoolExecutor
from django.http.request import HttpRequest
from rest_framework.views import APIView
from rest_framework.exceptions import APIException
from rest_framework.authentication import BasicAuthentication

log = logging.getLogger(__name__)
loop = asyncio.get_event_loop()
io_pool_exc = ThreadPoolExecutor(max_workers=2)
loop.set_default_executor(io_pool_exc)  # This is also done in the handler.py, is this unnecessary?

@middleware
async def authenticate(request, handler):
    """Authenticates the request to the content app using the DRF authentication classes"""
    django_request = convert_request(request)
    fake_view = APIView()  # might need to put a name here or something

    def _authenticate_blocking():
        drf_request = fake_view.initialize_request(django_request)
        try:
            fake_view.perform_authentication(drf_request)
        except APIException as e:
            log.warning(f'"{request.method} {request.path}" "{request.host}": {e}')  # maybe change to User-Agent?

        return drf_request

    auth_request = await loop.run_in_executor(None, _authenticate_blocking)
    request["user"] = auth_request.user  # These two fields are set on the request by DRF
    request["auth"] = auth_request.auth
    request["drf_request"] = auth_request  # Maybe useful to pass along for someone else?

    return await handler(request)


def convert_request(request):
    """
    Converts an aiohttp Request to a Django HttpRequest

    This does not convert the async body to a sync body
    """
    djr = HttpRequest()
    djr.method = request.method
    upper_keys = {k.upper() for k in request.headers.keys()}
    h = {"CONTENT_LENGTH", "CONTENT_TYPE"}
    djr.META = {f'HTTP_{k}' if k not in h else k: request.headers[k] for k in upper_keys}
    djr.COOKIES = request.cookies
    djr.path = request.path
    djr.path_info = request.match_info.get("path", "")
    djr.encoding = request.charset
    # djr.content_type = request.content_type
    # djr.content_params = request._content_dict  # Not sure if this is the best or correct
    djr.GET = request.query  # Hope this is compatible, could use QueryDict(request.query_string)
    # Do I need to set a resolver_match? https://docs.djangoproject.com/en/3.2/ref/request-response/#django.http.HttpRequest.resolver_match

    djr._get_scheme = lambda: request.scheme
    return djr
