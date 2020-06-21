import time
import logging

from ocr.sigma.config import Configuration
from ocr.sigma.statistics import get_detect_count

_logger = logging.getLogger(__name__)


class Query(object):
    """Get data from PACS and process them."""

    def __init__(self, conf=None):
        """Initialize the classes and build jobs pipeline."""
        if conf is None:
            conf = Configuration()
        self._context = conf.get_context()
        category = conf.get_database()
        if category == 'sqlite':
            from ocr.sigma.database.autorun import SQLite
            from ocr.sigma.request.sigmaserver import ServerRequest
            sqlite = conf.fetch('database', 'sqlite')
            self._database = SQLite(sqlite['db_name'])
            server = self._context['server']
            self._request = ServerRequest(server['endpoint'], access_key=server['key'], secret_key=server['secret'])
            _logger.info('AutoRun mode')
        elif category == 'mongodb':
            from ocr.sigma.database.sigmadicom import MongoDB
            from ocr.sigma.request.sigmacloud import CloudRequest
            mongodb = conf.fetch('database', 'mongodb')
            self._database = MongoDB(mongodb['db_name'], mongodb['hostnames'])
            server = self._context['server']
            self._request = CloudRequest(server['endpoint'], access_key=server['key'], secret_key=server['secret'], account=server['account'])
            _logger.info('SigmaDicom mode')

    def get_series(self, latest, **kwargs):
        """Get series accord by kwargs conditions."""
        if "series_instance_uid" not in kwargs \
                and "study_instance_uid" not in kwargs \
                and "patient_id" not in kwargs \
                and "accession_number" not in kwargs:
            raise ValueError("The input parameter was missing")
        # Only query succeed
        results = self._database.find(latest, **kwargs)
        for result in results:
            if result['status'] in ['computed', 'pushing', 'succeed', 'hanged']:
                try:
                    result['lesion_count'] = get_detect_count(result, self.get_json)
                except Exception as e:
                    _logger.warning(e)
            elif result['status'] == 'waiting':
                try:
                    job_data = self._request.get_job(result['job_id'])
                except Exception as e:
                    _logger.warning(e)
                else:
                    result['order_number'] = job_data.get('queue', {}).get('location')
                    if result['order_number'] is not None:
                        result['wait_time'] = result['order_number'] * 2        # x2 cost time
        return results

    def get_json(self, unique_id):
        return self._request.get_json(unique_id)

    def raise_priority(self, unique_id):
        result = {}
        priority_data = self._request.raise_priority(unique_id)
        result['job_id'] = priority_data['job_id']
        result['order_number'] = priority_data.get('queue', {}).get('location')
        if result['order_number'] is not None:
            result['wait_time'] = result['order_number'] * 2        # x2 cost time
        return result
