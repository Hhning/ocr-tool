import os
import logging

from pymongo import MongoClient

from ocr.sigma.database.abstract import AbstractDataBase


_logger = logging.getLogger(__name__)


JOB_TYPE_TRANS = {
    "lung_nodule_detection": "lung_nodule_det",
    "lung_dr_detection": "lung_dr_det",
    "mammo_detection": "mammo_det",
    "brain_detection": "brain_det"
}

STATUS_TRANS = {
    "inited": "waiting",
    "waiting": "waiting",
    "running": "running",
    "success": "computed",
    "pushing": "pushing",
    "pushed": "succeed",
    "failed": "failed",
    "push_hanged": "hanged"
}


class MongoDB(AbstractDataBase):
    """Connect and query mongodb."""

    def connect(self):
        self._client = MongoClient(self.host_name)
        self._db = self._client[self.db_name]

    def close(self):
        self._client.close()
        _logger.debug("DB sigmadicom closed")

    def find(self, latest=True, **kwargs):
        """Find the records by kwargs."""
        queries = {}
        # if "status" in kwargs and kwargs["status"] is not None:
        #     queries["status"] = kwargs.get("status")
        if "series_instance_uid" in kwargs and kwargs["series_instance_uid"] is not None:
            queries["SeriesInstanceUID"] = kwargs.get("series_instance_uid")
        if "study_instance_uid" in kwargs and kwargs["study_instance_uid"] is not None:
            queries["StudyInstanceUID"] = kwargs.get("study_instance_uid")
        if "patient_id" in kwargs and kwargs["patient_id"] is not None:
            queries["PatientID"] = kwargs.get("patient_id")
        if "accession_number" in kwargs and kwargs["accession_number"] is not None:
            queries["AccessionNumber"] = kwargs.get("accession_number")

        matched_serieses = self._db.datasets.find(queries).sort([('_id', -1)])
        autorun_records = []
        for series in matched_serieses:
            record = self._db.autorun.find_one({"StudyInstanceUID": series.get('StudyInstanceUID'), "PatientID": series.get('PatientID')})
            if not record:
                continue
            autorun_records.append((series, record))
        if autorun_records and latest:
            autorun_records = [autorun_records[0]]

        job_types = []
        results = []
        for dataset, autorun in autorun_records:
            job_type = JOB_TYPE_TRANS.get(autorun['job_type'], autorun['job_type'])
            if job_type in job_types:   # only return latest same job type
                continue
            job_types.append(job_type)
            result = {
                'job_type': job_type,
                'job_id': autorun.get('job_id'),
                'patient_id': dataset.get('PatientID'),
                'study_instance_uid': dataset.get('StudyInstanceUID'),
                'series_instance_uid': dataset.get('SeriesInstanceUID'),
                'status': STATUS_TRANS.get(autorun['status'], autorun['status'])
            }
            results.append(result)
        return results
