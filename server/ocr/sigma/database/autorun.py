import os
import time
import sqlite3
import logging

from ocr.sigma.database.abstract import AbstractDataBase

_logger = logging.getLogger(__name__)


STATUS_TRANS = {
    "succeed": "computed",
    "pushed": "succeed"
}


class SQLite(AbstractDataBase):
    """Connect and query sqlite3."""

    def connect(self):
        if os.path.exists(self.db_name):
            self._client = sqlite3.connect(self.db_name, check_same_thread=False)
            self._client.row_factory = SQLite.dict_factory
            self._db = self._client.cursor()
        else:
            self._client = None
            self._db = None

    def close(self):
        if self._client:
            self._client.close()
            self._client = self._db = None
            _logger.debug("DB autorun closed")

    def check(self):
        if not self._db:
            self.connect()
        return self._db is not None

    def find(self, latest=True, **kwargs):
        """Find the records by kwargs."""
        if not self.check():
            return []
        command = "SELECT * FROM autorun WHERE "
        queries = []
        if "status" in kwargs and kwargs["status"] is not None:
            queries.append("status='%s'" % kwargs.get("status"))
        if "series_instance_uid" in kwargs and kwargs["series_instance_uid"] is not None:
            queries.append("series_instance_uid='%s'" % kwargs.get("series_instance_uid"))
        if "study_instance_uid" in kwargs and kwargs["study_instance_uid"] is not None:
            queries.append("study_instance_uid='%s'" % kwargs.get("study_instance_uid"))
        if "patient_id" in kwargs and kwargs["patient_id"] is not None:
            queries.append("patient_id='%s' COLLATE NOCASE" % kwargs.get("patient_id"))
        if "accession_number" in kwargs and kwargs["accession_number"] is not None:
            queries.append("accession_number='%s'" % kwargs.get("accession_number"))
        command += " and ".join(queries)
        _logger.debug("Fetchall SQL: '%s'" % command)
        result = self._db.execute(command).fetchall()
        if latest and len(result) > 1:
            return [sorted(result, key=lambda x: time.strptime(x['datetime'], '%a, %d %b %Y %H:%M:%S GMT'), reverse=True)[0]]
        else:
            return result

    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        if d['status'] in STATUS_TRANS.keys():
            d['status'] = STATUS_TRANS.get(d['status'])
        if 'type' in d.keys():
            d['job_type'] = d.pop('type')
        return d
