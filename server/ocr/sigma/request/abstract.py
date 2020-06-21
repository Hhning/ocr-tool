import base64
import hashlib
import hmac
import time
from abc import ABC, abstractmethod

import requests

try:
    from urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit


class AbstractRequest(ABC):
    """Request to sigma server."""

    AUTH_PREFIX = "12Sigma"
    AUTH_HEADERS_PREFIX = "x-sigma-"

    def __init__(self, endpoint, **kwargs):
        """Set initial parameters."""
        self.endpoint = endpoint if endpoint.startswith("http://") else "http://" + endpoint
        self.access_key = kwargs["access_key"]
        self.secret_key = kwargs["secret_key"]

    def _get_gmt_time(self):
        """Get formatted time (GMT time)."""
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

    def _convert_to_utf8(self, content):
        """Convert input string to utf-8 stype."""
        return content.encode("utf-8") if isinstance(content, str) else content

    def _format_http_headers(self, headers=None):
        """Format http headers, convert user-defined headers."""
        if headers is None:
            headers = dict()
        parsed = dict()

        for key in headers.keys():
            content = self._convert_to_utf8(headers[key])
            if key.lower().startswith(self.AUTH_HEADERS_PREFIX):
                parsed[key.lower().strip()] = content
            else:
                parsed[key.strip()] = content
        return parsed

    def _get_canonicalized_headers(self, headers):
        """Get canonicalized headers."""
        if not headers:
            headers = dict()
        canonicalized = []
        keys = sorted(headers.keys())
        for key in keys:
            if key.startswith(self.AUTH_HEADERS_PREFIX):
                canonicalized.append("%s:%s" % (key, headers[key].strip()))
        return "\n".join(canonicalized)

    def _get_canonicalized_resource(self, url):
        """Get parameters from URL and sort them."""
        parsed = urlsplit(url)
        if not parsed.query:
            return url[(len(parsed.scheme) + 3):].strip()
        query = "&".join(sorted(parsed.query.split("&")))
        canonicalized = (parsed.netloc + parsed.path + "?" + query)
        return canonicalized

    def _gen_sign(self, secret, verb, headers, url):
        """Generate signature for http request."""
        if headers is None:
            headers = dict()
        # Format http, convert prefix is x-sigma- to lower
        headers = self._format_http_headers(headers)
        # Get content-type and content-md5
        content_type = headers.get("Content-Type", "")
        content_md5 = headers.get("Content-Md5", "")
        # Get date from headers, date is GMT time
        date = headers.get("Date", "")
        if not date:
            raise ValueError("Http Date header is empty")
        if isinstance(date, bytes):
            date = date.decode("utf-8")
        if isinstance(content_type, bytes):
            content_type = content_type.decode("utf-8")
        if isinstance(content_md5, bytes):
            content_md5 = content_md5.decode("utf-8")
        # Get canonicalized headers
        canonicalized_headers = self._get_canonicalized_headers(headers)
        # Get canonicalized resource
        canonicalized_resource = self._get_canonicalized_resource(url)
        canonicalized = ""
        if canonicalized_headers:
            canonicalized += (canonicalized_headers + "\n" + canonicalized_resource)
        else:
            canonicalized += canonicalized_resource
        # Build canonicalized, if canonicalized_headers is empty, igore it
        sign = "\n".join([verb,
                          content_md5,
                          content_type,
                          date,
                          canonicalized])
        digest = hmac.new(secret.encode(), sign.encode(), hashlib.sha256).digest()
        signature = base64.b64encode(digest).strip()
        if isinstance(signature, bytes):
            signature = signature.decode("utf-8")
        return signature

    def _get_auth(self, key, secret, verb, headers, url):
        """Get Authorization for http request."""
        return self.AUTH_PREFIX + " " + key + ":" + self._gen_sign(secret, verb, headers, url)

    @abstractmethod
    def get_job(self, unique_id):
        """Get the job status."""
        pass

    @abstractmethod
    def get_json(self, unique_id):
        pass

    @abstractmethod
    def raise_priority(self, unique_id):
        pass
