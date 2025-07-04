import asyncio
import logging
from multidict import CIMultiDict
import os
import re
import socket
import struct
from gettext import gettext as _
from datetime import datetime, timedelta

from aiohttp.client_exceptions import ClientResponseError, ClientConnectionError
from aiohttp.web import FileResponse, StreamResponse, HTTPOk
from aiohttp.web_exceptions import (
    HTTPError,
    HTTPForbidden,
    HTTPFound,
    HTTPMovedPermanently,
    HTTPNotFound,
    HTTPRequestRangeNotSatisfiable,
)
from yarl import URL

from asgiref.sync import sync_to_async

import django
from django.utils import timezone

from pulpcore.constants import STORAGE_RESPONSE_MAP, CHECKPOINT_TS_FORMAT
from pulpcore.responses import ArtifactResponse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulpcore.app.settings")
django.setup()

from django.conf import settings  # noqa: E402: module level not at top of file
from django.core.exceptions import (  # noqa: E402: module level not at top of file
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.db import (  # noqa: E402: module level not at top of file
    connection,
    DatabaseError,
    IntegrityError,
    models,
    transaction,
)
from pulpcore.app.models import (  # noqa: E402: module level not at top of file
    Artifact,
    ArtifactDistribution,
    ContentArtifact,
    Distribution,
    Publication,
    Remote,
    RemoteArtifact,
)
from pulpcore.app import mime_types  # noqa: E402: module level not at top of file
from pulpcore.app.util import (  # noqa: E402: module level not at top of file
    get_domain,
    cache_key,
)

from pulpcore.exceptions import (  # noqa: E402
    UnsupportedDigestValidationError,
    DigestValidationError,
)
from pulpcore.metrics import artifacts_size_counter  # noqa: E402

from jinja2 import Template  # noqa: E402: module level not at top of file
from pulpcore.cache import AsyncContentCache  # noqa: E402

log = logging.getLogger(__name__)


class PathNotResolved(HTTPNotFound):
    """
    The path could not be resolved to a published file.

    This could be caused by either the distribution, the publication,
    or the published file could not be found.
    """

    def __init__(self, path, *args, **kwargs):
        """Initialize the Exception."""
        self.path = path
        super().__init__(*args, **kwargs)


class DistroListings(HTTPOk):
    """
    Response for browsing through the distributions and their potential multi-layered base-paths.

    This is returned when visiting the base path of the content app (/pulp/content/) or a partial
    base path of a distribution, e.g. /pulp/content/foo/ for distros /foo/bar/ & /foo/baz/
    """

    def __init__(self, path, distros):
        """Create the HTML response."""
        exclude = models.Q(pulp_type=ArtifactDistribution.get_pulp_type()) | models.Q(hidden=True)
        distros = distros.exclude(exclude)
        if settings.HIDE_GUARDED_DISTRIBUTIONS:
            distros = distros.filter(content_guard__isnull=True)
        base_paths = (
            distros.annotate(rel_path=models.functions.Substr("base_path", 1 + len(path)))
            .annotate(
                path=models.Func(
                    models.F("rel_path"),
                    function="SUBSTRING",
                    template="%(function)s(%(expressions)s,'([^/]*)')",
                )
            )
            .order_by("path")
            .values_list("path", flat=True)
            .distinct()
        )
        directory_list = (f"{b}/" for b in base_paths)
        if path == "":
            path = settings.CONTENT_PATH_PREFIX
        html = Handler.render_html(directory_list, path=path)
        super().__init__(body=html, headers={"Content-Type": "text/html"})


class CheckpointListings(HTTPOk):
    """
    Response for browsing through the checkpoints of a specific checkpoint distro.

    This is returned when visiting the base path of a checkpoint distro.
    """

    def __init__(self, path, repo):
        """Create the HTML response."""

        checkpoints = (
            Publication.objects.filter(repository_version__repository=repo, checkpoint=True)
            .order_by("pulp_created")
            .values_list("pulp_created", flat=True)
            .distinct()
        )
        dates = {f"{Handler._format_checkpoint_timestamp(s)}/": s for s in checkpoints}
        directory_list = dates.keys()
        html = Handler.render_html(directory_list, dates=dates, path=path)
        super().__init__(body=html, headers={"Content-Type": "text/html"})


class ArtifactNotFound(Exception):
    """
    The artifact associated with a published-artifact does not exist.
    """

    pass


class Handler:
    """
    A default Handler for the Content App that also can be subclassed to create custom handlers.

    This Handler will perform the following:

    1. Match the request against a Distribution

    2. Call the certguard check if a certguard exists for the matched Distribution.

    3. If the Distribution has a `publication` serve that Publication's `PublishedArtifacts`,
       `PublishedMetadata` by the remaining `relative path`. If still unserved and if `pass_through`
       is set, the associated `repository_version` will have its `ContentArtifacts` served by
       `relative_path` also. This will serve the associated `Artifact`.

    4. If still unmatched, and the Distribution has a `repository` attribute set, find it's latest
       `repository_version`. If the Distribution has a `repository_version` attribute set, use that.
       For this `repository_version`, find matching `ContentArtifact` objects by `relative_path` and
       serve them. If there is an associated `Artifact` return it.

    5. If the Distribution has a `remote`, find an associated `RemoteArtifact` that matches by
       `relative_path`. Fetch and stream the corresponding `RemoteArtifact` to the client,
       optionally saving the `Artifact` depending on the `policy` attribute.

    """

    hop_by_hop_headers = [
        "connection",
        "content-encoding",
        "content-length",
        "keep-alive",
        "public",
        "proxy-authenticate",
        "transfer-encoding",
        "upgrade",
    ]

    distribution_model = None

    @staticmethod
    def _reset_db_connection():
        """
        Reset database connection if it's unusable or obselete to avoid "connection already closed".
        """
        connection.close_if_unusable_or_obsolete()

    async def list_distributions(self, request):
        """
        The handler for an HTML listing all distributions

        Args:
            request (aiohttp.web.request) The request from the client.

        Raises:
            [aiohttp.web.HTTPOk][]: The response back to the client.
            [PathNotResolved][]: 404 error response when path doesn't exist.
        """
        domain = get_domain()

        if not request.path.endswith("/"):
            raise HTTPMovedPermanently(f"{request.path}/")

        def get_base_paths_blocking():
            distro_model = self.distribution_model or Distribution
            raise DistroListings(path="", distros=distro_model.objects.filter(pulp_domain=domain))

        if request.method.lower() == "head":
            raise HTTPOk(headers={"Content-Type": "text/html"})
        await sync_to_async(get_base_paths_blocking)()

    @classmethod
    async def find_base_path_cached(cls, request, cached):
        """
        Finds the base-path to use for the base-key in the cache

        Args:
            request (aiohttp.web.request) The request from the client.
            cached (CacheAiohttp) The Pulp cache

        Returns:
            str: The base-path associated with this request
        """
        path = request.match_info["path"]
        base_paths = cls._base_paths(path)
        multiplied_base_paths = []
        for i, base_path in enumerate(base_paths):
            copied_by_index_base_path = cache_key([base_path for _ in range(i + 1)])
            multiplied_base_paths.extend(copied_by_index_base_path)
        index_p1 = await cached.exists(base_key=multiplied_base_paths)
        if index_p1:
            return cache_key(base_paths[index_p1 - 1])
        else:
            distro = await sync_to_async(cls._match_distribution)(
                path, add_trailing_slash=cached.ADD_TRAILING_SLASH
            )
            return cache_key(distro.base_path)

    @classmethod
    async def auth_cached(cls, request, cached, base_key):
        """
        Authentication check for the cached stream_content handler

        Args:
            request (aiohttp.web.request) The request from the client.
            cached (CacheAiohttp) The Pulp cache
            base_key (str): The base_key associated with this response
        """
        guard_key = "DISTRO#GUARD#PRESENT"
        present = await cached.get(guard_key, base_key=base_key)
        if present == b"True" or present is None:
            path = request.match_info["path"]
            distro = await sync_to_async(cls._match_distribution)(
                path, add_trailing_slash=cached.ADD_TRAILING_SLASH
            )
            try:
                guard = await sync_to_async(cls._permit)(request, distro)
            except HTTPForbidden:
                guard = True
                raise
            finally:
                if not present:
                    await cached.set(guard_key, str(guard), base_key=base_key)

    @AsyncContentCache(
        base_key=lambda req, cac: Handler.find_base_path_cached(req, cac),
        auth=lambda req, cac, bk: Handler.auth_cached(req, cac, bk),
    )
    async def stream_content(self, request):
        """
        The request handler for the Content app.

        Args:
            request (aiohttp.web.request) The request from the client.

        Returns:
            [aiohttp.web.StreamResponse][] or [aiohttp.web.FileResponse][]: The response
                back to the client.
        """
        path = request.match_info["path"]
        return await self._match_and_stream(path, request)

    @staticmethod
    def _base_paths(path):
        """
        Get a list of base paths used to match a distribution.

        Args:
            path (str): The path component of the URL.

        Returns:
            list: Of base paths.

        """
        tree = []
        while True:
            base = os.path.split(path)[0]
            if not base.lstrip("/"):
                break
            tree.append(base)
            path = base
        return tree

    @classmethod
    def _match_distribution(cls, path, add_trailing_slash=True):
        """
        Match a distribution using a list of base paths and return its detail object.

        Args:
            path (str): The path component of the URL.
            add_trailing_slash (bool): If true, a missing trailing '/' will be appended to the path.

        Returns:
            The detail object of the matched distribution.

        Raises:
            DistroListings: when multiple matches are possible.
            PathNotResolved: when not matched.
        """
        original_path = path
        path_ends_in_slash = path.endswith("/")
        if not path_ends_in_slash and add_trailing_slash:
            path = f"{path}/"
        base_paths = cls._base_paths(path)
        distro_model = cls.distribution_model or Distribution
        domain = get_domain()
        try:
            distro_object = (
                distro_model.objects.filter(pulp_domain=domain)
                .select_related(
                    "repository",
                    "repository_version",
                    "repository_version__repository",
                    "publication",
                    "remote",
                    "pulp_domain",
                    "publication__repository_version",
                )
                .get(base_path__in=base_paths)
                .cast()
            )
            return distro_object
        except ObjectDoesNotExist:
            if path.rstrip("/") in base_paths:
                distros = distro_model.objects.filter(
                    pulp_domain=domain, base_path__startswith=path
                )
                if distros.count():
                    if path_ends_in_slash:
                        raise DistroListings(path=path, distros=distros)
                    else:
                        # The list of a subset of distributions was requested without a trailing /
                        Handler._redirect_sub_path(path)

            log.debug(
                _("Distribution not matched for {path} using: {base_paths}").format(
                    path=original_path, base_paths=base_paths
                )
            )

        raise PathNotResolved(original_path)

    @classmethod
    def _select_checkpoint_publication(cls, distro, path):
        """
        Finds the checkpoint publication to serve based on the checkpoint distribution and path.

        Args:
            distro (Distribution): The checkpoint distribution.
            path (str): The checkpoint path component of the URL (e.g. 20250212T194653Z/dists/).

        Returns:
            The detail object of the selected publication.

        Raises:
            PathNotResolved: when the path is invalid.
            CheckpointListings: when the path is the base path of a checkpoint distribution.
        """
        # Determine whether it's a listing or a specific checkpoint
        if path == "":
            raise CheckpointListings(path=path, repo=distro.repository)
        else:
            request_timestamp, rel_path = Handler._parse_checkpoint_path(path)

            # Find the latest checkpoint publication before or at the timestamp
            checkpoint_publication = (
                Publication.objects.filter(
                    pulp_created__lte=request_timestamp,
                    repository_version__repository=distro.repository,
                    checkpoint=True,
                )
                .order_by("-pulp_created")
                .first()
            )

            if not checkpoint_publication:
                raise PathNotResolved(path)

            pub_timestamp_str = Handler._format_checkpoint_timestamp(
                checkpoint_publication.pulp_created
            )
            request_timestamp_str = Handler._format_checkpoint_timestamp(request_timestamp)
            if pub_timestamp_str != request_timestamp_str:
                Handler._redirect_sub_path(f"{distro.base_path}/{pub_timestamp_str}/{rel_path}")

            return checkpoint_publication

    @staticmethod
    def _parse_checkpoint_path(path):
        """
        Validate the path and extract the timestamp and rel_path from it.

        Args:
            path (str): The checkpoint path component of the URL (e.g. 20250212T194653Z/dists/).

        Returns:
            tuple: The timestamp and the relative path.

        Raises:
            PathNotResolved: when the path is invalid.
        """
        pattern = r"^(\d{8}T\d{6}Z)/?(.*)?$"
        match = re.search(pattern, path)
        if match:
            request_timestamp_str = match.group(1)
            try:
                request_timestamp = datetime.strptime(request_timestamp_str, CHECKPOINT_TS_FORMAT)
            except ValueError:
                raise PathNotResolved(path)
        else:
            raise PathNotResolved(path)

        request_timestamp = request_timestamp.replace(tzinfo=timezone.utc)
        # Future timestamps are not allowed for checkpoints
        if request_timestamp > datetime.now(tz=timezone.utc):
            raise PathNotResolved(path)
        # The timestamp is truncated to seconds, so we need to cover the whole second
        request_timestamp = request_timestamp.replace(microsecond=999999)

        rel_path = match.group(2)
        return request_timestamp, rel_path

    @staticmethod
    def _format_checkpoint_timestamp(timestamp):
        """
        Format a timestamp to the checkpoint format.

        Args:
            timestamp (datetime): The timestamp to format.

        Returns:
            The formatted timestamp using the `CHECKPOINT_TS_FORMAT`.
        """
        return datetime.strftime(timestamp, CHECKPOINT_TS_FORMAT)

    @staticmethod
    def _redirect_sub_path(path):
        """
        Redirect to the correct path based on whether domain is enabled.

        Args:
            path (str): The path component after the path prefix.

        Raises:
            HTTPMovedPermanently: to the correct path.
        """
        if settings.DOMAIN_ENABLED:
            raise HTTPMovedPermanently(f"{settings.CONTENT_PATH_PREFIX}{get_domain().name}/{path}")
        else:
            raise HTTPMovedPermanently(f"{settings.CONTENT_PATH_PREFIX}{path}")

    @staticmethod
    def _permit(request, distribution):
        """
        Permit the request.

        Authorization is delegated to the optional content-guard associated with the distribution.

        Args:
            request (aiohttp.web.Request) A request for a published file.
            distribution (detail of [pulpcore.plugin.models.Distribution][]): The matched
                distribution.

        Raises:
            [aiohttp.web_exceptions.HTTPForbidden][]: When not permitted.
        """
        guard = distribution.content_guard
        if not guard:
            return False
        try:
            guard.cast().permit(request)
        except PermissionError as pe:
            log.debug(
                'Path: %(p)s not permitted by guard: "%(g)s" reason: %(r)s',
                {"p": request.path, "g": guard.name, "r": str(pe)},
            )
            raise HTTPForbidden(reason=str(pe))
        return True

    @staticmethod
    def response_headers(path, distribution=None):
        """
        Get the Content-Type and Encoding-Type headers for the requested `path`.

        Args:
            path (str): The relative path that was requested.
            distribution(Distribution) : Distribution detail that might want to add headers for path
        Returns:
            headers (dict): A dictionary of response headers.
        """
        # headers are case-insensitive
        headers = CIMultiDict({})

        # Determine a content-type from mime_types and set.
        # Note: plugin-Distribution can override this.
        content_type = mime_types.get_type(path)
        if content_type:
            headers["Content-Type"] = content_type

        # Let plugin-Distribution set headers for this path if it wants.
        if distribution:
            headers.update(distribution.content_headers_for(path))

        return headers

    @staticmethod
    def render_html(directory_list, path="", dates=None, sizes=None):
        """
        Render a list of strings as an HTML list of links.

        Args:
            directory_list (iterable): an iterable of strings representing file and directory names

        Returns:
            String representing HTML of the directory listing.
        """
        dates = dates or {}
        sizes = sizes or {}
        root = path == settings.CONTENT_PATH_PREFIX
        if root and settings.DOMAIN_ENABLED:
            path += f"{get_domain().name}/"
        template = Template(
            """
<html>
<head><title>Index of {{ path }}</title></head>
<body bgcolor="white">
<h1>Index of {{ path }}</h1>
<hr><pre>
{%- if not root %}<a href="../">../</a>{% endif %}
{% for name in dir_list -%}
{% if dates.get(name, "") -%}
{% set date = dates.get(name).strftime("%d-%b-%Y %H:%M") -%}
{% else -%}
{% set date = "" -%}
{% endif -%}
{% if name in sizes -%}
{% set size | filesizeformat -%}
{{ sizes.get(name) }}
{% endset -%}
{% else -%}
{% set size = "" -%}
{% endif -%}
<a href="{{ name|e }}">{{ name|e }}</a>{% for number in range(100 - name|e|length) %} """
            """{% endfor %}{{ date }}  {{ size }}
{% endfor -%}
</pre><hr></body>
</html>
"""
        )
        return template.render(
            dir_list=sorted(directory_list),
            dates=dates,
            path=path,
            root=root,
            sizes=sizes,
        )

    async def list_directory(self, repo_version, publication, path):
        """
        Generate a set with directory listing of the path.

        This method expects either a repo_version or a publication in addition to a path. This
        method generates a set of strings representing the list of a path inside the repository
        version or publication.

        Args:
            repo_version (pulpcore.app.models.RepositoryVersion) The repository version
            publication (pulpcore.app.models.Publication) Publication
            path (str): relative path inside the repo version of publication.

        Returns:
            Set of strings representing the files and directories in the directory listing.
        """

        def file_or_directory_name(directory_path, relative_path):
            result = re.match(r"({})([^\/]*)(\/*)".format(re.escape(directory_path)), relative_path)
            return "{}{}".format(result.groups()[1], result.groups()[2])

        def list_directory_blocking():
            if not publication and not repo_version:
                raise Exception("Either a repo_version or publication is required.")
            if publication and repo_version:
                raise Exception("Either a repo_version or publication can be specified.")
            content_repo_ver = repo_version or publication.repository_version
            directory_list = set()
            dates = {}
            content_to_find = {}
            sizes = {}
            artifacts_to_find = {}

            if publication:
                pas = publication.published_artifact.select_related(
                    "content_artifact__artifact"
                ).filter(relative_path__startswith=path)
                for pa in pas:
                    name = file_or_directory_name(path, pa.relative_path)
                    directory_list.add(name)
                    dates[name] = pa.pulp_created
                    content_to_find[pa.content_artifact.content_id] = name
                    if pa.content_artifact.artifact:
                        sizes[name] = pa.content_artifact.artifact.size
                    else:
                        artifacts_to_find[pa.content_artifact.pk] = name

            if repo_version or publication.pass_through:
                cas = ContentArtifact.objects.select_related("artifact").filter(
                    content__in=content_repo_ver.content, relative_path__startswith=path
                )
                for ca in cas:
                    name = file_or_directory_name(path, ca.relative_path)
                    directory_list.add(name)
                    dates[name] = ca.pulp_created
                    content_to_find[ca.content_id] = name
                    if ca.artifact:
                        sizes[name] = ca.artifact.size
                    else:
                        artifacts_to_find[ca.pk] = name

            if directory_list:
                # Find the dates the content got added to the repository
                dates.update(
                    {
                        content_to_find[rc.content_id]: rc.pulp_created
                        for rc in content_repo_ver._content_relationships()
                        if rc.content_id in content_to_find
                    }
                )
                # Find the sizes for on_demand artifacts
                r_artifacts = RemoteArtifact.objects.filter(
                    content_artifact__in=artifacts_to_find.keys(), size__isnull=False
                ).values_list("content_artifact_id", "size")
                sizes.update({artifacts_to_find[ra_ca_id]: size for ra_ca_id, size in r_artifacts})

            return directory_list, dates, sizes

        return await sync_to_async(list_directory_blocking)()

    async def _match_and_stream(self, path, request):
        """
        Match the path and stream results either from the filesystem or by downloading new data.

        After deciding the client can access the distribution at ``path``, this function calls
        :meth:`Distribution.content_handler`. If that function returns a not-None result, it is
        returned to the client.

        Then the publication linked to the Distribution is used to determine what content should
        be served. If ``path`` is a directory entry (i.e. not a file), the directory contents
        are served to the client. This method calls
        :meth:`Distribution.content_handler_list_directory` to acquire any additional entries the
        Distribution's content_handler might serve in that directory. If there is an Artifact to be
        served, it is served to the client.

        If there's no publication, the above paragraph is applied to the latest repository linked
        to the matched Distribution.

        Finally, when nothing is served to client yet, we check if there is a remote for the
        Distribution. If so, the Artifact is pulled from the remote and streamed to the client.

        Args:
            path (str): The path component of the URL.
            request(aiohttp.web.Request) The request to prepare a response for.

        Raises:
            PathNotResolved: The path could not be matched to a published file.
            PermissionError: When not permitted.

        Returns:
            [aiohttp.web.StreamResponse][] or [aiohttp.web.FileResponse][]: The response
                streamed back to the client.
        """
        distro = await sync_to_async(self._match_distribution)(path)

        await sync_to_async(self._permit)(request, distro)

        rel_path = path.lstrip("/")
        rel_path = rel_path[len(distro.base_path) :]
        rel_path = rel_path.lstrip("/")

        if rel_path == "" and not path.endswith("/"):
            # The root of a distribution base_path was requested without a slash
            raise HTTPMovedPermanently(f"{request.path}/")

        original_rel_path = rel_path
        ends_in_slash = rel_path == "" or rel_path.endswith("/")
        if not ends_in_slash:
            rel_path = f"{rel_path}/"

        headers = self.response_headers(original_rel_path, distro)

        content_handler_result = await sync_to_async(distro.content_handler)(original_rel_path)
        if content_handler_result is not None:
            if isinstance(content_handler_result, ContentArtifact):
                if content_handler_result.artifact:
                    return await self._serve_content_artifact(
                        content_handler_result, headers, request
                    )
                else:
                    return await self._stream_content_artifact(
                        request, StreamResponse(headers=headers), content_handler_result
                    )
            else:
                # the result is a response so just return it
                return content_handler_result

        if distro.checkpoint:
            repository = repo_version = None
            publication = await sync_to_async(self._select_checkpoint_publication)(
                distro, original_rel_path
            )
            # Remove the timestamp from the path to get the relative path for the publication
            rel_path = rel_path.split("/", 1)[1]
            original_rel_path = original_rel_path.split("/", 1)[1]
        else:
            repository = distro.repository
            publication = distro.publication
            repo_version = distro.repository_version

        if repository:
            repository = await repository.acast()
            # Search for publication serving the latest (last complete) version
            if not publication:
                try:
                    versions = repository.versions.all()
                    publications = Publication.objects.filter(
                        repository_version__in=versions, complete=True
                    )
                    publication = await publications.select_related("repository_version").alatest(
                        "repository_version", "pulp_created"
                    )
                    repo_version = publication.repository_version
                except ObjectDoesNotExist:
                    pass

            if not repo_version:
                repo_version = await repository.alatest_version()

        if publication:
            try:
                index_path = "{}index.html".format(rel_path)

                await publication.published_artifact.aget(relative_path=index_path)
                if not ends_in_slash:
                    # index.html found, but user didn't specify a trailing slash
                    raise HTTPMovedPermanently(f"{request.path}/")
                original_rel_path = index_path
                headers = self.response_headers(original_rel_path, distro)
            except ObjectDoesNotExist:
                dir_list, dates, sizes = await self.list_directory(None, publication, rel_path)
                dir_list.update(
                    await sync_to_async(distro.content_handler_list_directory)(rel_path)
                )
                if dir_list and not ends_in_slash:
                    # Directory can be listed, but user did not specify trailing slash
                    raise HTTPMovedPermanently(f"{request.path}/")
                elif dir_list:
                    return HTTPOk(
                        headers={"Content-Type": "text/html"},
                        body=self.render_html(
                            dir_list, path=request.path, dates=dates, sizes=sizes
                        ),
                    )

            # published artifact
            try:
                ca = (
                    await publication.published_artifact.select_related(
                        "content_artifact",
                        "content_artifact__artifact",
                        "content_artifact__artifact__pulp_domain",
                    ).aget(relative_path=original_rel_path)
                ).content_artifact

            except ObjectDoesNotExist:
                pass
            else:
                if ca.artifact:
                    return await self._serve_content_artifact(ca, headers, request)
                else:
                    return await self._stream_content_artifact(
                        request, StreamResponse(headers=headers), ca
                    )

            # pass-through
            if publication.pass_through:
                try:
                    ca = (
                        await ContentArtifact.objects.select_related(
                            "artifact", "artifact__pulp_domain"
                        )
                        .filter(
                            content__in=publication.repository_version.content,
                        )
                        .aget(relative_path=original_rel_path)
                    )

                except MultipleObjectsReturned:
                    log.error(
                        "Multiple (pass-through) matches for {b}/{p}",
                        {"b": distro.base_path, "p": original_rel_path},
                    )
                    raise
                except ObjectDoesNotExist:
                    pass
                else:
                    if ca.artifact:
                        return await self._serve_content_artifact(ca, headers, request)
                    else:
                        return await self._stream_content_artifact(
                            request, StreamResponse(headers=headers), ca
                        )

        if repo_version and not publication and not distro.SERVE_FROM_PUBLICATION:
            # Look for index.html or list the directory
            index_path = "{}index.html".format(rel_path)

            contentartifact_exists = await ContentArtifact.objects.filter(
                content__in=repo_version.content, relative_path=index_path
            ).aexists()
            if contentartifact_exists:
                original_rel_path = index_path
                headers = self.response_headers(original_rel_path, distro)
            else:
                dir_list, dates, sizes = await self.list_directory(repo_version, None, rel_path)
                dir_list.update(
                    await sync_to_async(distro.content_handler_list_directory)(rel_path)
                )
                if dir_list and not ends_in_slash:
                    # Directory can be listed, but user did not specify trailing slash
                    raise HTTPMovedPermanently(f"{request.path}/")
                elif dir_list:
                    return HTTPOk(
                        headers={"Content-Type": "text/html"},
                        body=self.render_html(
                            dir_list, path=request.path, dates=dates, sizes=sizes
                        ),
                    )

            try:
                ca = await ContentArtifact.objects.select_related(
                    "artifact", "artifact__pulp_domain"
                ).aget(content__in=repo_version.content, relative_path=original_rel_path)

            except MultipleObjectsReturned:
                log.error(
                    "Multiple (pass-through) matches for {b}/{p}",
                    {"b": distro.base_path, "p": original_rel_path},
                )
                raise
            except ObjectDoesNotExist:
                pass
            else:
                if ca.artifact:
                    return await self._serve_content_artifact(ca, headers, request)
                else:
                    return await self._stream_content_artifact(
                        request, StreamResponse(headers=headers), ca
                    )

        # If we haven't found a match yet, try to use pull-through caching with remote
        if distro.remote:
            remote = await distro.remote.acast()
            if url := remote.get_remote_artifact_url(original_rel_path, request=request):
                if (
                    ra := await RemoteArtifact.objects.select_related(
                        "content_artifact__artifact__pulp_domain", "remote"
                    )
                    .filter(remote=remote, url=url)
                    .afirst()
                ):
                    ca = ra.content_artifact
                    # Try to add content to repository if present & supported
                    if repository and repository.PULL_THROUGH_SUPPORTED:
                        await sync_to_async(repository.pull_through_add_content)(ca)
                    # Try to stream the ContentArtifact if already created
                    if ca.artifact:
                        return await self._serve_content_artifact(ca, headers, request)
                    else:
                        return await self._stream_content_artifact(
                            request, StreamResponse(headers=headers), ca
                        )
                else:
                    # Try to stream the RemoteArtifact and potentially save it as a new Content unit
                    save_artifact = (
                        remote.get_remote_artifact_content_type(original_rel_path) is not None
                    )
                    ca = ContentArtifact(relative_path=original_rel_path)
                    ra = RemoteArtifact(remote=remote, url=url, content_artifact=ca)
                    try:
                        return await self._stream_remote_artifact(
                            request,
                            StreamResponse(headers=headers),
                            ra,
                            save_artifact=save_artifact,
                            repository=repository,
                        )
                    except ClientResponseError as ce:

                        class Error(HTTPError):
                            status_code = ce.status

                        reason = _("Error while fetching from upstream remote({url}): {r}").format(
                            url=url, r=ce.message
                        )
                        raise Error(reason=reason)

        if not any([repository, repo_version, publication, distro.remote]):
            reason = _(
                "Distribution is not pointing to a publication, repository, repository version,"
                " or remote."
            )
        else:
            reason = None
        raise PathNotResolved(path, reason=reason)

    async def _stream_content_artifact(self, request, response, content_artifact):
        """
        Stream and optionally save a ContentArtifact by requesting it using the associated remote.

        If a fatal download failure occurs while downloading and there are additional
        [pulpcore.plugin.models.RemoteArtifact][] objects associated with the
        [pulpcore.plugin.models.ContentArtifact][] they will also be tried. If all
        [pulpcore.plugin.models.RemoteArtifact][] downloads raise exceptions, an HTTP 502
        error is returned to the client.

        Args:
            request(aiohttp.web.Request) The request to prepare a response for.
            response (aiohttp.web.StreamResponse) The response to stream data to.
            content_artifact (pulpcore.plugin.models.ContentArtifact) The ContentArtifact
                to fetch and then stream back to the client

        Raises:
            [aiohttp.web.HTTPNotFound][] when no
                [pulpcore.plugin.models.RemoteArtifact][] objects associated with the
                [pulpcore.plugin.models.ContentArtifact][] returned the binary data needed for
                the client.
        """
        # We should only skip exceptions that happen before we receive any data
        # and start streaming, as we can't rollback data if something happens after that.
        SKIPPABLE_EXCEPTIONS = (
            ClientResponseError,
            UnsupportedDigestValidationError,
            ClientConnectionError,
        )

        protection_time = settings.REMOTE_CONTENT_FETCH_FAILURE_COOLDOWN
        remote_artifacts = (
            content_artifact.remoteartifact_set.select_related("remote")
            .order_by_acs()
            .exclude(failed_at__gte=timezone.now() - timedelta(seconds=protection_time))
        )
        async for remote_artifact in remote_artifacts:
            try:
                response = await self._stream_remote_artifact(request, response, remote_artifact)
                return response
            except SKIPPABLE_EXCEPTIONS as e:
                log.warning(
                    "Could not download remote artifact at '{}': {}".format(
                        remote_artifact.url, str(e)
                    )
                )
                continue

        raise HTTPNotFound()

    def _save_artifact(self, download_result, remote_artifact, request=None):
        """
        Create/Get an Artifact and associate it to a RemoteArtifact and/or ContentArtifact.

        Create (or get if already existing) an [pulpcore.plugin.models.Artifact][]
        based on the `download_result` and associate it to the `content_artifact` of the given
        `remote_artifact`. Both the created artifact and the updated content_artifact are saved to
        the DB.  The `remote_artifact` is also saved for the pull-through caching use case.

        Plugin-writers may overide this method if their content module requires
        additional/different steps for saving.

        Args:
            download_result ([pulpcore.plugin.download.DownloadResult][]: The
                DownloadResult for the downloaded artifact.

            remote_artifact (pulpcore.plugin.models.RemoteArtifact) The
                RemoteArtifact to associate the Artifact with.

            request (aiohttp.web.Request) The request.

        Returns:
            A dictionary of created ContentArtifact objects by relative path.
        """
        content_artifact = remote_artifact.content_artifact
        remote = remote_artifact.remote
        artifact = Artifact(**download_result.artifact_attributes, file=download_result.path)
        cas = []
        with transaction.atomic():
            try:
                with transaction.atomic():
                    artifact.save()
            except IntegrityError:
                try:
                    artifact = Artifact.objects.get(artifact.q())
                    artifact.touch()
                except (Artifact.DoesNotExist, DatabaseError):
                    # it's possible that orphan cleanup deleted the artifact
                    # so fall back to creating a new artifact again
                    artifact = Artifact(
                        **download_result.artifact_attributes, file=download_result.path
                    )
                    artifact.save()
                else:
                    # The file needs to be unlinked because it was not used to create an artifact.
                    # The artifact must have already been saved while servicing another request for
                    # the same artifact.
                    os.unlink(download_result.path)

            if content_artifact._state.adding:
                # This is the first time pull-through content was requested.
                rel_path = content_artifact.relative_path
                c_type = remote.get_remote_artifact_content_type(rel_path)
                artifacts = {rel_path: artifact}
                content = c_type.init_from_artifact_and_relative_path(artifact, rel_path)
                if isinstance(content, tuple):
                    content, artifacts = content
                try:
                    with transaction.atomic():
                        content.save()
                        for relative_path, c_artifact in artifacts.items():
                            new_ca = ContentArtifact(
                                relative_path=relative_path, artifact=c_artifact, content=content
                            )
                            new_ca.save()
                            cas.append(new_ca)
                except IntegrityError:
                    # There is already content saved
                    content = c_type.objects.get(content.q())
                    # Update the ContentArtifacts to point to the new Artifacts
                    cas = list(content.contentartifact_set.select_related("artifact"))
                    if len(cas) == 0 or any(ca.artifact is None for ca in cas):
                        new_cas = [
                            ContentArtifact(artifact=a, content=content, relative_path=rp)
                            for rp, a in artifacts.items()
                        ]
                        ContentArtifact.objects.bulk_create(
                            new_cas,
                            update_conflicts=True,
                            update_fields=["artifact"],
                            unique_fields=["content", "relative_path"],
                        )
                        cas = list(content.contentartifact_set.select_related("artifact"))
                # Now try to save RemoteArtifacts for each ContentArtifact
                for ca in cas:
                    if url := remote.get_remote_artifact_url(ca.relative_path, request=request):
                        ra = RemoteArtifact(remote=remote, content_artifact=ca, url=url)
                        try:
                            with transaction.atomic():
                                ra.save()
                        except IntegrityError:
                            # Remote artifact must have already been saved during a parallel request
                            log.info(f"RemoteArtifact for {url} already exists.")
            else:
                # Normal on-demand downloading, update CA to point to new saved Artifact
                content_artifact.artifact = artifact
                content_artifact.save()
        ret = {content_artifact.relative_path: content_artifact}
        if cas:
            ret.update({ca.relative_path: ca for ca in cas})
        return ret

    def _build_response_from_content_artifact(self, content_artifact, headers, request):
        """Helper method to build the correct response to serve a ContentArtifact."""

        def _set_params_from_headers(hdrs, storage_domain):
            # Map standard-response-headers to storage-object-specific keys
            params = {}
            if storage_domain in STORAGE_RESPONSE_MAP:
                for a_key in STORAGE_RESPONSE_MAP[storage_domain]:
                    if hdrs.get(a_key, None):
                        params[STORAGE_RESPONSE_MAP[storage_domain][a_key]] = hdrs[a_key]
            return params

        def _build_url(**kwargs):
            filename = os.path.basename(content_artifact.relative_path)
            content_disposition = f"attachment;filename={filename}"

            headers["Content-Disposition"] = content_disposition
            parameters = _set_params_from_headers(headers, domain.storage_class)
            storage_url = storage.url(artifact_name, parameters=parameters, **kwargs)

            return URL(storage_url, encoded=True)

        artifact_file = content_artifact.artifact.file
        artifact_name = artifact_file.name
        domain = get_domain()
        storage = domain.get_storage()
        headers["X-PULP-ARTIFACT-SIZE"] = str(artifact_file.size)

        if domain.storage_class == "pulpcore.app.models.storage.FileSystem":
            path = storage.path(artifact_name)
            if not os.path.exists(path):
                raise Exception(_("Expected path '{}' is not found").format(path))
            return FileResponse(path, headers=headers)
        elif not domain.redirect_to_object_storage:
            return ArtifactResponse(content_artifact.artifact, headers=headers)
        elif domain.storage_class == "storages.backends.s3boto3.S3Boto3Storage":
            return HTTPFound(_build_url(http_method=request.method), headers=headers)
        elif domain.storage_class in (
            "storages.backends.azure_storage.AzureStorage",
            "storages.backends.gcloud.GoogleCloudStorage",
        ):
            return HTTPFound(_build_url(), headers=headers)
        else:
            raise NotImplementedError()

    async def _serve_content_artifact(self, content_artifact, headers, request):
        """
        Handle response for a Content Artifact with the file present.

        Depending on where the file storage (e.g. filesystem, S3, etc) this could be responding with
        the file (filesystem) or a redirect (S3).

        Args:
            content_artifact (pulpcore.app.models.ContentArtifact) The Content Artifact to
                respond with.
            headers (dict): A dictionary of response headers.
            request(aiohttp.web.Request) The request to prepare a response for.

        Raises:
            [aiohttp.web_exceptions.HTTPFound][]: When we need to redirect to the file
            NotImplementedError: If file is stored in a file storage we can't handle
            HTTPRequestRangeNotSatisfiable: If the request is for a range that is not
                satisfiable.
        Returns:
            The [aiohttp.web.FileResponse][] for the file.
        """
        artifact_file = content_artifact.artifact.file
        content_length = artifact_file.size

        try:
            range_start, range_stop = request.http_range.start, request.http_range.stop
            if range_start or range_stop:
                if range_stop and artifact_file.size and range_stop > artifact_file.size:
                    start = 0 if range_start is None else range_start
                    content_length = artifact_file.size - start
                elif range_stop:
                    content_length = range_stop - range_start
        except ValueError:
            size = artifact_file.size or "*"
            raise HTTPRequestRangeNotSatisfiable(headers={"Content-Range": f"bytes */{size}"})

        artifacts_size_counter.add(content_length)

        response = self._build_response_from_content_artifact(content_artifact, headers, request)
        if isinstance(response, HTTPFound):
            raise response
        else:
            return response

    async def _stream_remote_artifact(
        self, request, response, remote_artifact, save_artifact=True, repository=None
    ):
        """
        Stream and save a RemoteArtifact.

        Args:
            request(aiohttp.web.Request) The request to prepare a response for.
            response (aiohttp.web.StreamResponse) The response to stream data to.
            remote_artifact (pulpcore.plugin.models.RemoteArtifact) The RemoteArtifact
                to fetch and then stream back to the client
            save_artifact (bool): Override the save behavior on the streamed RemoteArtifact
            repository (:class:`~pulpcore.plugin.models.Repository`): An optional repository to save
                the content to if supported

        Raises:
            [aiohttp.web.HTTPNotFound][] when no
                [pulpcore.plugin.models.RemoteArtifact][] objects associated with the
                [pulpcore.plugin.models.ContentArtifact][] returned the binary data needed for
                the client.

        """

        remote = await remote_artifact.remote.acast()
        log.debug(
            "Streaming content for {url} from Remote {remote}-{source}".format(
                url=request.match_info["path"], remote=remote.name, source=remote_artifact.url
            )
        )

        # According to RFC7233 if a server cannot satisfy a Range request, the response needs to
        # contain a Content-Range header with an unsatisfied-range value.
        try:
            range_start, range_stop = request.http_range.start, request.http_range.stop
            size = remote_artifact.size
            if size and range_start and range_start >= size:
                raise HTTPRequestRangeNotSatisfiable(headers={"Content-Range": f"bytes */{size}"})

        except ValueError:
            size = remote_artifact.size or "*"
            raise HTTPRequestRangeNotSatisfiable(headers={"Content-Range": f"bytes */{size}"})

        original_headers = response.headers.copy()
        actual_content_length = None

        if range_start or range_stop:
            response.set_status(206)
            if range_stop and size and range_stop > size:
                start = 0 if range_start is None else range_start
                actual_content_length = size - start

        async def handle_response_headers(headers):
            for name, value in headers.items():
                lower_name = name.lower()
                if lower_name not in self.hop_by_hop_headers:
                    response.headers[name] = value
                elif response.status == 206 and lower_name == "content-length":
                    content_length = int(value)
                    start = 0 if range_start is None else range_start
                    if range_stop is None:
                        stop = content_length
                    elif actual_content_length:
                        stop = start + actual_content_length
                    else:
                        stop = range_stop

                    range_bytes = stop - start
                    if actual_content_length:
                        response.headers[name] = str(actual_content_length)
                    else:
                        response.headers[name] = str(range_bytes)

                    # aiohttp adds a 1 to the range.stop compared to http headers (including) to
                    # match python array adressing (exclusive)
                    response.headers["Content-Range"] = "bytes {0}-{1}/{2}".format(
                        start, stop - 1, content_length
                    )

            content_encoding = headers.get("content-encoding")
            content_length = headers.get("content-length")
            if content_length and not content_encoding:
                response.headers["X-PULP-ARTIFACT-SIZE"] = content_length
                artifacts_size_counter.add(content_length)

            await response.prepare(request)

        data_size_handled = 0

        async def handle_data(data):
            nonlocal data_size_handled
            # If we got here, and the response hasn't had "prepare()" called on it, it's due to
            # some code-path (i.e., FileDownloader) that doesn't know/care about
            # headers_ready_callback failing to invoke it.
            # We're not going to do anything more with headers at this point, so it's safe to
            # "backstop" the prepare() call here, so the write() will be allowed.
            if not response.prepared:
                await response.prepare(request)
            if request.method == "GET":
                if range_start or range_stop:
                    start_byte_pos = 0
                    end_byte_pos = len(data)
                    if range_start:
                        start_byte_pos = max(0, range_start - data_size_handled)
                    if range_stop:
                        end_byte_pos = min(len(data), range_stop - data_size_handled)

                    data_for_client = data[start_byte_pos:end_byte_pos]
                    await response.write(data_for_client)
                    data_size_handled = data_size_handled + len(data)
                else:
                    await response.write(data)
            if remote.policy != Remote.STREAMED:
                await original_handle_data(data)

        async def finalize():
            if save_artifact and remote.policy != Remote.STREAMED:
                await original_finalize()

        downloader = remote.get_downloader(
            remote_artifact=remote_artifact,
            headers_ready_callback=handle_response_headers,
        )
        original_handle_data = downloader.handle_data
        downloader.handle_data = handle_data
        original_finalize = downloader.finalize
        downloader.finalize = finalize
        try:
            download_result = await downloader.run(
                extra_data={"disable_retry_list": (DigestValidationError,)}
            )
        except DigestValidationError:
            remote_artifact.failed_at = timezone.now()
            await remote_artifact.asave()
            close_tcp_connection(request.transport._sock)
            REMOTE_CONTENT_FETCH_FAILURE_COOLDOWN = settings.REMOTE_CONTENT_FETCH_FAILURE_COOLDOWN
            raise RuntimeError(
                f"Pulp tried streaming {remote_artifact.url!r} to "
                "the client, but it failed checksum validation.\n\n"
                "We can't recover from wrong data already sent so we are:\n"
                "- Forcing the connection to close.\n"
                "- Marking this Remote to be ignored for "
                f"{REMOTE_CONTENT_FETCH_FAILURE_COOLDOWN=}s.\n\n"
                "If the Remote is known to be fixed, try resyncing the associated repository.\n"
                "If the Remote is known to be permanently corrupted, try removing "
                "affected Pulp Remote, adding a good one and resyncing.\n"
                "Learn more on <https://pulpproject.org/pulpcore/docs/user/learn/"
                "on-demand-downloading/#on-demand-and-streamed-limitations>"
            )

        if save_artifact and remote.policy != Remote.STREAMED:
            content_artifacts = await asyncio.shield(
                sync_to_async(self._save_artifact)(download_result, remote_artifact, request)
            )
            ca = content_artifacts[remote_artifact.content_artifact.relative_path]
            # If cache is enabled, add the future response to our stream response
            if settings.CACHE_ENABLED:
                response.future_response = self._build_response_from_content_artifact(
                    ca, original_headers, request
                )
            # Try to add content to repository if present & supported
            if repository and repository.PULL_THROUGH_SUPPORTED:
                await sync_to_async(repository.pull_through_add_content)(ca)
        await response.write_eof()

        if response.status == 404:
            raise HTTPNotFound()
        return response


def close_tcp_connection(sock):
    """Configure socket to close TCP connection immediately."""
    try:
        l_onoff = 1
        l_linger = 0  # 0 seconds timeout - immediate close
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", l_onoff, l_linger))
    except (socket.error, OSError) as e:
        log.warning(f"Error configuring socket for force close: {e}")
