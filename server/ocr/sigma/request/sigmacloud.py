import base64
import hashlib
import hmac
import json
import logging
import time

import requests

from ocr.sigma.request.abstract import AbstractRequest

_logger = logging.getLogger(__name__)

SELF_DEFINE_HEADER_PREFIX = "x-sigma-"
SELF_DEFINE_AUTH_PREFIX = "12Sigma"


def extract_resource_from_url(url):
    if url.lower().startswith("http://"):
        idx = url.find('/', 7, -1)
        return url[idx:].strip()
    elif url.lower().startswith("https://"):
        idx = url.find('/', 8, -1)
        return url[idx:].strip()
    else:
        return url.strip()


def format_header(headers=None):
    """
    format the headers that self define
    convert the self define headers to lower.
    """
    if not headers:
        headers = {}
    tmp_headers = {}

    for k in headers.keys():
        tmp_str = headers[k]
        if k.lower().startswith(SELF_DEFINE_HEADER_PREFIX):
            k_lower = k.lower().strip()
            tmp_headers[k_lower] = tmp_str
        else:
            tmp_headers[k.strip()] = tmp_str
    return tmp_headers


def canonicalize_resource(resource):
    res_list = resource.split("?")
    if len(res_list) <= 1 or len(res_list) > 2:
        return resource
    res = res_list[0]
    param = res_list[1]
    params = param.split("&")
    params = sorted(params)
    param = '&'.join(params)
    return res + '?' + param


class SigmaAuth(requests.auth.AuthBase):
    def __init__(self, access_key_id, access_key_secret, verbose=True):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.verbose = verbose
        if verbose:
            _logger.debug("Initialize SigmaAuth, access key id: " + access_key_id +
                          ", access key secret: " + access_key_secret)

    def __call__(self, r):
        method = r.method
        content_type = r.headers.get('Content-Type', '')
        content_md5 = r.headers.get('Content-MD5', '')
        canonicalized_gd_headers = ""
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

        resource = extract_resource_from_url(r.url)

        tmp_headers = format_header(r.headers)
        if len(tmp_headers) > 0:
            x_header_list = tmp_headers.keys()
            # x_header_list.sort()
            for k in x_header_list:
                if k.startswith(SELF_DEFINE_HEADER_PREFIX):
                    canonicalized_gd_headers += "%s:%s\n" % (k, tmp_headers[k])

        canonicalized_resource = canonicalize_resource(resource)
        if self.verbose:
            _logger.debug("Canonicalized resource: " + canonicalized_resource)

        string_to_sign = method + "\n" + content_md5 + "\n" + content_type + "\n" + date + "\n" + canonicalized_gd_headers + canonicalized_resource
        if self.verbose:
            _logger.debug("String to Sign: " + string_to_sign)

        try:
            h = hmac.new(self.access_key_secret.encode(), string_to_sign.encode(), hashlib.sha256)
            signature = base64.b64encode(h.digest()).strip()
            if isinstance(signature, bytes):
                signature = signature.decode("utf-8")

            r.headers["Date"] = date
            r.headers["Authorization"] = SELF_DEFINE_AUTH_PREFIX + " " + self.access_key_id + ":" + signature
            if self.verbose:
                _logger.info("Authorization header: " + r.headers["Authorization"])
        except Exception as e:
            _logger.warning(e)

        return r



class CloudRequest(AbstractRequest):
    """Request to SigmaCloud."""

    JOB_STATUS_TRANS = {
        "waiting": "waiting",
        "running": "running",
        "crashed": "failed",
        "completed": "succeed"
    }

    def __init__(self, endpoint, **kwargs):
        """Set initial parameters."""
        super().__init__(endpoint, **kwargs)
        self.account = kwargs["account"]

    def get_job(self, unique_id):
        headers = {'Content': 'application/json'}
        url = '{}/accounts/{}/jobs/{}/?queue_info=true'.format(self.endpoint, self.account, unique_id)

        response = requests.get(url, headers=headers, auth=SigmaAuth(self.access_key, self.secret_key))
        if response.status_code // 100 == 2:
            return json.loads(response.text)['data']
        else:
            raise ValueError(response.text)

    def get_json(self, unique_id):
        headers = {'Content': 'application/json'}
        url = '{}/accounts/{}/store/downloads/?filename={}.json'.format(self.endpoint, self.account, unique_id)

        resp1 = requests.get(url, headers=headers, auth=SigmaAuth(self.access_key, self.secret_key))
        if resp1.status_code // 100 == 2:
            url = '{}&download_id={}'.format(url1, json.loads(resp1.text)['download_id'])
            resp2 = requests.get(url, headers=headers, auth=SigmaAuth(self.access_key, self.secret_key))
            if resp2.status_code // 100 == 2:
                return json.loads(resp2.text)
            else:
                raise ValueError(resp2.text)
        else:
            raise ValueError(resp1.text)

    def raise_priority(self, unique_id):
        headers = {'Content': 'application/json'}
        url = '{}/accounts/{}/jobs/{}/'.format(self.endpoint, self.account, unique_id)

        response = requests.patch(url, data={"priority": 3}, headers=headers, auth=SigmaAuth(self.access_key, self.secret_key))
        if response.status_code // 100 == 2:
            priority_data = json.loads(response.text)
            return self.get_job(priority_data['data']['job_id'])
        else:
            raise ValueError(response.text)
