import os
import sys
import json
import logging
import logging.handlers
import traceback

from PyQt5.QtWidgets import QMessageBox

from sigmaris.config import appConfig
from sigmaris.config import ROOT_PATH, DEBUG_PATH, LOG_PATH, APP_CONFIG

_logger = logging.getLogger()

if not appConfig.debug:
    _logger.setLevel(logging.INFO)
else:
    _logger.setLevel(logging.DEBUG)
    os.makedirs(DEBUG_PATH, exist_ok=True)

# timed rotating file
os.makedirs(LOG_PATH, exist_ok=True)
_logFileName = os.path.join(LOG_PATH, 'sigmaris.log')
_fileHandler = logging.handlers.TimedRotatingFileHandler(_logFileName, when='midnight', encoding='utf-8')
_streamHandler = logging.StreamHandler()

# formatter
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(lineno)d: %(message)s')

_fileHandler.setFormatter(_formatter)
_streamHandler.setFormatter(_formatter)

_logger.addHandler(_fileHandler)
_logger.addHandler(_streamHandler)

_logger.info('APPROOT: {}'.format(ROOT_PATH))
_logger.info('CONFIG_PATH: {}'.format(APP_CONFIG))
_logger.info('LOG_PATH: {}'.format(LOG_PATH))
_logger.info('DEBUG_PATH: {}'.format(DEBUG_PATH))
_logger.debug('Config: \n{}'.format(json.dumps(appConfig._data, indent=4)))


def showException(error):
    QMessageBox.critical(None, 'SigmaRIS', error, QMessageBox.Abort)


def myExceptHook(type, value, tb):
    errorInfo = "".join(traceback.format_exception(type, value, tb))
    for line in errorInfo.strip().split("\n"):
        _logger.info(line)
    _logger.error("unhandled exception")
    showException(errorInfo)
    sys.exit(2)

sys.excepthook = myExceptHook
