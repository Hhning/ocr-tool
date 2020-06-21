import logging
import json
import os
import subprocess

import requests
from requests.compat import urljoin
from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QDesktopServices

from sigmaris.config import ROOT_PATH, appConfig

CONFIG = os.path.join(ROOT_PATH, 'web.json')

_logger = logging.getLogger(__name__)
_content = None
_token = None
_timer = None


def get_web_json():
    global _content
    with open(CONFIG) as f:
        _content = json.load(f)
    return _content


def login():
    assert _content
    global _token
    url = urljoin(_content['server'], '/login')
    headers = {'Content-Type':'application/json', 'Remote-Ip': _content.get('remote-ip', 'x.x.x.x'), 'Remote-Mac-Address': _content.get('remote-mac-address', 'y-y-y-y-y-y')}
    params = {'account_name': _content['account'], 'user_name': _content['username'], 'password': _content['password'], 'force_new_session': 'false'}
    try:
        response = requests.get(url, params=params, headers=headers)
    except requests.ConnectionError:
        _token = None
        _logger.warning('Login failed!')
        return

    if response.status_code == 200:
        _token = response.json()['data']['user_info']['token']
        _logger.info('Login sucess!')
    else:
        _token = None
        _logger.warning('Login failed!')


def _refresh():
    if appConfig['Launcher']['type'] == 'Web':
        login()


def init_token_config():
    if appConfig['Launcher']['type'] != 'Web':
        return

    get_web_json()
    login()
    if not _token:
        QMessageBox.warning(None, 'SigmaRIS', 'Login failed!', QMessageBox.Ok)


def init_token_timer(parent):
    global _timer
    if not _timer:
        init_token_config()
        _timer = QTimer(parent)
        _timer.timeout.connect(_refresh)
        _timer.start(3600000)     # 1h


def open_url(series_id):
    if not _token:
        _logger.warning('Token is invalid!')
        return
    url = appConfig['Launcher']['command']['Web'].format(_content['website'], _token, series_id)
    browser = appConfig['Launcher']['path']['Web']
    if not browser:
        QDesktopServices.openUrl(QUrl(url))
    else:
        subprocess.Popen([browser, url], shell=True)
