import json

import requests

from ocr.sigma.request.abstract import AbstractRequest


class ServerRequest(AbstractRequest):
    """Request to SigmaServer."""

    JOB_STATUS_TRANS = {
        "waiting": "waiting",
        "running": "running",
        "crashed": "failed",
        "completed": "succeed"
    }

    def __init__(self, endpoint, **kwargs):
        """Set initial parameters."""
        super().__init__(endpoint, **kwargs)

    def get_job(self, unique_id):
        headers = dict()
        headers["Content-Type"] = "application/json"
        headers["Date"] = self._get_gmt_time()

        url = '{}/jobs?unique_id={}'.format(self.endpoint, unique_id)
        auth = self._get_auth(self.access_key, self.secret_key, "GET", headers, url)
        headers["Authorization"] = auth

        response = requests.get(url, headers=headers)
        if response.status_code // 100 == 2:
            data = json.loads(response.text)
            for job in data:
                return self.JOB_STATUS_TRANS.get(job.get("status"))
        else:
            raise ValueError(response.text)

    def get_json(self, unique_id):
        headers = dict()
        headers["Content-Type"] = "application/json"
        headers["Date"] = self._get_gmt_time()

        url = '{}/data/downloads/{}?format=json&category=original'.format(self.endpoint, unique_id)
        auth = self._get_auth(self.access_key, self.secret_key, "GET", headers, url)
        headers["Authorization"] = auth

        response = requests.get(url, headers=headers)
        if response.status_code // 100 == 2:
            return json.loads(response.text)
        else:
            raise ValueError(response.text)

    def raise_priority(self, unique_id):
        raise NotImplementedError
