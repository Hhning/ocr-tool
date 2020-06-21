import logging
from collections import OrderedDict

import requests
from requests.compat import urljoin

from sigmaris.config import appConfig
from sigmaris.constants import FAILED_STRING, WAITING_STRING, RUNNING_STRING, SUCCEED_STRING, UNKNOWN_STRING, COMPUTED_STRING, PUSHING_STRING, HANGED_STRING
from sigmaris.constants import DEFAULT_VALUE, WAITING_VALUE, RUNNING_VALUE, HEALTH_VALUE, DISEASE_VALUE, FAILED_VALUE


ORDER_DICT = {
    SUCCEED_STRING: 0,
    RUNNING_STRING: 1,
    WAITING_STRING: 2,
    FAILED_STRING: 3,
    UNKNOWN_STRING: 4,
}

VALUE_DICT = {
    RUNNING_STRING: RUNNING_VALUE,
    WAITING_STRING: WAITING_VALUE,
    FAILED_STRING: FAILED_VALUE,
}

_logger = logging.getLogger(__name__)
session = requests.Session()


class DetectionInfo(object):

    def __init__(self, patient_id=None, study_instance_uid=None, series_instance_uid=None, accession_number=None, status=UNKNOWN_STRING, **kw):
        self.patient_id = patient_id
        self.study_id = study_instance_uid
        self.series_id = series_instance_uid
        self.accession_number = accession_number
        self.status = status
        if appConfig['Launcher']['type'] == 'Web':
            if self.status in [COMPUTED_STRING, PUSHING_STRING, HANGED_STRING]:     # SigmaWeb don't push
                self.status = SUCCEED_STRING
        else:
            if self.status in [COMPUTED_STRING, PUSHING_STRING]:
                self.status = RUNNING_STRING
            elif self.status == HANGED_STRING:
                self.status = FAILED_STRING
        
        self.detect_type = kw.get('job_type', 'lung_nodule_det')
        self.lesion_count = kw.get('lesion_count', 0)
        self.order_number = kw.get('order_number')
        self.wait_time = kw.get('wait_time')
        self.job_time = kw.get('job_time')
        self.job_id = kw.get('job_id')

    def value(self):
        if self.status == SUCCEED_STRING:
            return DISEASE_VALUE if self.lesion_count > 0 else HEALTH_VALUE
        else:
            return VALUE_DICT.get(self.status, DEFAULT_VALUE)

    def __lt__(self, other):
        if ORDER_DICT[self.status] <= ORDER_DICT[other.status]:
            return True
        return False

    def __repr__(self):
        return 'patient_id: {patient_id}, study_id: {study_id}, series_id: {series_id}, accession_number: {accession_number}, status: {status}'.format(**self.__dict__)


class QueryResult(object):

    def __init__(self, result):
        self._detections = OrderedDict()
        for data in result:
            info = DetectionInfo(**data)
            self._detections[info.detect_type] = info

    @property
    def default(self) -> DetectionInfo:
        for d in self:
            return d

    @property
    def count(self):
        return len(self._detections)

    @property
    def detections(self):
        return self._detections.keys()

    def hasOne(self, detection):
        return detection in self._detections.keys()

    def getOne(self, detection=None, default=True) -> DetectionInfo:
        one = self._detections.get(detection)
        if not one and default:
            return self.default
        else:
            return one

    def anyDone(self):
        for d in self:
            if d.status == SUCCEED_STRING:
                return d.detect_type

    def allDone(self):
        for k, v in self._detections.items():
            if v.status != SUCCEED_STRING:
                return False
        else:
            return self._detections and True or False

    def __iter__(self):
        ordered = sorted(self._detections.values())
        for o in ordered:
            yield o


def setupOCR(files, **kw):
    url = urljoin(appConfig['Server']['endpoint'], '/ocr/')
    _files = [('file', f) for f in files]
    response = session.post(url, data=kw, files=_files, timeout=3)
    if not 200 <= response.status_code < 300:
        response.raise_for_status()
    result = response.json()['data']
    assert isinstance(result, list) or isinstance(result, tuple)
    text, threshold = result
    _logger.info('SetupOCR: {}, {}'.format(text, threshold))
    return text, threshold


def applyOCR(files, **kw):
    url = urljoin(appConfig['Server']['endpoint'], '/ocr/')
    _files = [('file', f) for f in files]
    response = session.post(url, data=kw, files=_files, timeout=3)
    if not 200 <= response.status_code < 300:
        response.raise_for_status()
    result = response.json()['data']
    _logger.info('ApplyOCR: {}'.format(result))
    return result


def getStatus(text):
    if not text:
        return
    keyword = appConfig['Server']['keyword']
    if not keyword or keyword not in ['patient_id', 'study_id', 'series_id', 'accession_number']:
        kw = {'patient_id': text}       # default patient_id
    else:
        kw = {keyword: text}

    url = urljoin(appConfig['Server']['endpoint'], '/autorun/series')
    headers = {'Content-Type': 'application/json'}
    params = {
        'patient_id': kw.get('patient_id'),
        'study_instance_uid': kw.get('study_id'),
        'series_instance_uid': kw.get('series_id'),
        'accession_number': kw.get('accession_number'),
        'latest': False
    }
    response = session.get(url, headers=headers, params=params, timeout=2)
    if not 200 <= response.status_code < 300:
        response.raise_for_status()

    info = None
    data = response.json()['data']
    if data:
        detections = appConfig['Launcher'].get('detections', [])
        _data = list(filter(lambda i: i.get('job_type') in detections, data))
        if _data:
            info = QueryResult(_data)
    _logger.debug('Query id: {}, result: {}'.format(text, info))
    return info


def pipeline(files, data):
    text = applyOCR(files, **data)
    if not text:
        return
    result = getStatus(text)
    return text, result


def raisePriority(job_id):
    if not job_id:
        return
    url = urljoin(appConfig['Server']['endpoint'], '/raise/{}'.format(job_id))
    headers = {'Content-Type': 'application/json'}
    response = session.put(url, headers=headers, timeout=1)
    if not 200 <= response.status_code < 300:
        response.raise_for_status()
    return response.json()['data']
