import os
import json
import codecs
import pathlib
import tempfile
from collections import OrderedDict

from .utils import singleton, runAsAdmin

USER_PATH = os.getenv('APPDATA')
_ROOT_PATH = pathlib.PurePath(__file__).parent.parent
ROOT_PATH = str(_ROOT_PATH)
_APP_CONFIG = pathlib.PurePath(_ROOT_PATH, 'app.json')
APP_CONFIG = str(_APP_CONFIG)
LOG_PATH = str(pathlib.PurePath(USER_PATH, 'SigmaRIS', 'log'))
DEBUG_PATH = str(pathlib.PurePath(USER_PATH, 'SigmaRIS', 'debug'))
ROI_PATH = str(pathlib.PurePath(USER_PATH, 'SigmaRIS', 'ROI'))

os.makedirs(ROI_PATH, exist_ok=True)


@singleton
class AppConfig(object):

    def __init__(self):
        self._data = {}
        self._debug = False

    @property
    def debug(self):
        return self._debug

    def load(self):
        # with open(APP_CONFIG, encoding='utf-8') as fp:
        with codecs.open(APP_CONFIG, 'r', 'utf-8-sig') as fp:
            self._data = json.load(fp, object_pairs_hook=OrderedDict)
        self._debug = self._data.get('Debug', False)

    def dump(self):
        content = json.dumps(self._data, indent=4, ensure_ascii=False)
        try:
            with open(APP_CONFIG, 'w', encoding='utf-8') as fp:
                fp.write(content)
        except PermissionError:
            tmp = os.path.join(tempfile.gettempdir(), 'SigmaRIS-config.json')
            with open(tmp, 'w', encoding='utf-8') as fp:
                fp.write(content)
            try:
                ret = runAsAdmin([os.path.join(ROOT_PATH, 'move.bat'), tmp])
            except:         # cancel UAC
                self.load()
            else:
                if ret != 0:    # move failed
                    self.load()

    def get(self, key, fallback=None):
        return self._data.get(key, fallback)
    
    def set(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data.get(key)

    def __setitem__(self, key, value):
        self._data[key] = value

appConfig = AppConfig()
appConfig.load()
