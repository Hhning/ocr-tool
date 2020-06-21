# -*- coding=utf-8 -*-
#
"""Auto service for query dicom series status."""
#
from __future__ import absolute_import

import collections
import json
import logging
import logging.config
import os
import shutil
import time
import tempfile
import traceback

from flask import Flask, make_response, request
from flask_cors import CORS

from ocr import __version__
from ocr.sigma import conf
from ocr.engine import SigmaOCR
from ocr.sigma.query import Query

HTTP_PORT_SERVICE = 7002

logger = logging.getLogger("autoserv")

logger.info("VERSION: {}".format(__version__))
logger.info("Configuration: {}".format(conf.get_context()))

OCR_IMAGE_STORE_PATH = conf.get_dirname().get("ocr", "C:\\12sigma\\autorun\\ocr")
if not os.path.exists(OCR_IMAGE_STORE_PATH):
    os.makedirs(OCR_IMAGE_STORE_PATH)

OCR_WHITE_LIST = conf.get_ocr_white_list()
logger.info("OCR white list: {}".format(OCR_WHITE_LIST))

PATTERN_STR = conf.get_ocr_pattern()
logger.info("OCR pattern: {}".format(PATTERN_STR))

OCR_LENGTH = conf.get_ocr_length()
logger.info("OCR length: {}".format(OCR_LENGTH))

OCR_OFFSET = conf.get_ocr_offset()
logger.info("OCR offset: {}".format(OCR_OFFSET))

app = Flask("autoserv")
cors = CORS(app)
query = Query(conf)
engine = SigmaOCR(PATTERN_STR)
engine.set_length(OCR_LENGTH)
engine.set_whitelist_char(OCR_WHITE_LIST)
engine.set_offset(OCR_OFFSET)


@app.route("/autorun/series", methods=["GET"])
def get_series():
    """Get series by patient_id, accession_number, study_instance_uid."""
    response = {"message": "", "message_chs": "", "error": {
        "code": "", "message": "", "message_chs": ""}, "data": None}
    kwargs = {}
    if "series_instance_uid" in request.args:
        kwargs["series_instance_uid"] = request.args.get("series_instance_uid")
        if kwargs["series_instance_uid"] == "None":
            kwargs["series_instance_uid"] = None

    if "study_instance_uid" in request.args:
        kwargs["study_instance_uid"] = request.args.get("study_instance_uid")
        if kwargs["study_instance_uid"] == "None":
            kwargs["study_instance_uid"] = None

    if "patient_id" in request.args:
        kwargs["patient_id"] = request.args.get("patient_id")
        if kwargs["patient_id"] == "None":
            kwargs["patient_id"] = None

    if "accession_number" in request.args:
        kwargs["accession_number"] = request.args.get("accession_number")
        if kwargs["accession_number"] == "None":
            kwargs["accession_number"] = None

    if "status" in request.args:
        kwargs["status"] = request.args.get("status")
        if kwargs["status"] == "None":
            kwargs["status"] = None

    if not kwargs:
        response["error"]["code"] = "InvalidInput"
        response["error"]["message"] = "The request argument was missing"
        response["error"]["message"] = "缺少参数!"
        return make_response(json.dumps(response), 400)

    latest = request.args.get('latest', 'True').lower() == 'true'
    result = query.get_series(latest, **kwargs)
    if latest:
        result = {} if not result else result[0]
    logger.info("get series process status {}".format(result))
    response["message"] = "Get status successfully!"
    response["message_chs"] = "获取状态成功!"
    response["data"] = result
    return make_response(json.dumps(response), 200)


def workspace():
    date = time.strftime('%Y%m%d', time.localtime())
    date_dir = os.path.join(OCR_IMAGE_STORE_PATH, date)
    os.makedirs(date_dir, exist_ok=True)
    return date_dir


@app.route("/autorun/json", methods=["GET"])
def get_json():
    """Get series by patient_id, accession_number, study_instance_uid."""
    response = {"message": "", "message_chs": "", "error": {
        "code": "", "message": "", "message_chs": ""}, "data": None}
    series_id = request.args.get("series_instance_uid")
    if not series_id:
        response["error"]["code"] = "InvalidInput"
        response["error"]["message"] = "The request argument was missing"
        response["error"]["message"] = "缺少参数!"
        return make_response(json.dumps(response), 400)

    json_data = query.get_json(series_id)

    logger.info("get json result {}".format(json_data))
    response["message"] = "Get json successfully!"
    response["message_chs"] = "获取结果成功!"
    response["data"] = json_data
    return make_response(json.dumps(response), 200)


@app.route("/raise/<string:job_id>", methods=["PUT"])
def raise_priority(job_id):
    """Get series by patient_id, accession_number, study_instance_uid."""
    response = {"message": "", "message_chs": "", "error": {
        "code": "", "message": "", "message_chs": ""}, "data": None}
    if not job_id:
        response["error"]["code"] = "InvalidInput"
        response["error"]["message"] = "The request argument was missing"
        response["error"]["message"] = "缺少参数!"
        return make_response(json.dumps(response), 400)

    priority_data = query.raise_priority(job_id)

    logger.info("raise priority result {}".format(priority_data))
    response["message"] = "Raise priority successfully!"
    response["message_chs"] = "提升优先级成功!"
    response["data"] = priority_data
    return make_response(json.dumps(response), 200)


@app.route("/ocr/", methods=["POST"])
def ocr():
    """OCR process."""
    response = {"message": "", "message_chs": "", "error": {"code": "", "message": "", "message_chs": ""}, "data": ""}
    file_storages = request.files.getlist('file')
    patient_id = request.form.get('patient_id', '')
    threshold = {}
    image_dir = tempfile.mkdtemp(dir=workspace())
    logger.info('OCR image_dir: {}'.format(image_dir))
    for file_storage in file_storages:
        file_name = file_storage.filename
        file_path = os.path.join(image_dir, file_name)
        file_storage.save(file_path)
        thres = request.form.get('threshold+{}'.format(file_name))
        if thres:
            threshold[file_name] = int(thres)
    if len(file_storages) == 1 and not patient_id and not threshold:
        logger.debug('legacy ocr')
        image_file = os.path.join(image_dir, file_storages[0].filename)
        result = engine.ocr_legacy(image_file)
    else:
        logger.debug('future ocr')
        result = engine.ocr_process(os.path.join(OCR_IMAGE_STORE_PATH, 'sigma-ocr.json'), image_dir, threshold, patient_id)
    logger.info('ocr result: {}'.format(result))
    response["data"] = result
    response["message"] = "get optical character successfully!"
    response["message_chs"] = "字符识别成功!"
    return make_response(json.dumps(response), 200)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=HTTP_PORT_SERVICE, debug=False)
