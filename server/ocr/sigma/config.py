import codecs
import logging
import os
import pathlib
import platform

import yaml

# Set the runtime log folder name
LOG_FOLDER_NAME = "log"
# OCR image storage path
OCR_FOLDER_NAME = "ocr"



def config_logging_environment(log_file_path=None):
    defaults = {
        'version': 1,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'stream': 'ext://sys.stderr',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filename': '{}'.format(log_file_path if log_file_path is not None else "autoserv.log"),
                'mode': 'a',
                'maxBytes': 10485760,
                'backupCount': 20,
            },
        },
        'formatters': {
            'detailed': {
                'format': "%(asctime)-15s %(levelname)-8s %(filename)-17s line:%(lineno)-4d %(message)s"
            }
        },
        'loggers': {
            '': {
                'level': 'DEBUG',
                'handlers': ['file', 'console', ]
            }
        }
    }

    logging.config.dictConfig(defaults)


class Configuration(object):
    """Parse the yaml configuration and validate them."""

    def __init__(self, conf=None):
        """Parser yaml configure and initial workspace."""
        if conf:
            filename = conf
        else:
            root_dir = pathlib.Path(__file__).parent.parent.parent
            filename = str(pathlib.Path(root_dir, 'conf', 'ocr.yml'))
        if not os.path.exists(filename):
            raise ValueError("The configure %s not exists" % filename)
        self._context = self._get_context(filename)
        self._dirname = {}
        mongodb = self._context['database'].get('mongodb')
        sqlite = self._context['database'].get('sqlite')
        if mongodb and mongodb.get('db_name') and mongodb.get('hostnames'):
            if platform.system() == "Windows":
                raise ValueError('mongodb only support docker')
            self._dirname = self._makedirs('/root/12sigma')
        elif sqlite and sqlite.get('db_name'):
            if not sqlite['db_name'].endswith('.db'):
                raise ValueError('sqlite db error')
            data_dir = str(pathlib.Path(sqlite['db_name']).parent.parent)
            self._dirname = self._makedirs(data_dir)
        else:
            raise ValueError('database config error')

    def __str__(self):
        """Print the configuration."""
        return "DIRNAME: %s, CONTEXT: %s" % (str(self._dirname), str(self._context))

    def _get_context(self, filename):
        """Load and parser yaml configure file."""
        with codecs.open(filename, 'r', 'utf-8-sig') as fp:
            return yaml.load(fp)

    def _makedirs(self, dirname):
        """Make sub directory."""
        subitems = {}
        os.makedirs(dirname, exist_ok=True)
        log = os.path.join(dirname, LOG_FOLDER_NAME)
        os.makedirs(log, exist_ok=True)
        subitems[LOG_FOLDER_NAME] = log
        ocr_image = os.path.join(dirname, OCR_FOLDER_NAME)
        os.makedirs(log, exist_ok=True)
        subitems[OCR_FOLDER_NAME] = ocr_image
        return subitems

    def get_context(self):
        """Get the configure dict."""
        return self._context

    def get_dirname(self):
        """Get the workspace dict."""
        return self._dirname

    def get_ocr_white_list(self):
        return self._context.get("ocr", dict).get("whitelist", "0123456789")

    def get_ocr_pattern(self):
        return self._context.get("ocr", dict).get("pattern", '')

    def get_ocr_length(self):
        return self._context.get("ocr", dict).get("length", -1)

    def get_ocr_offset(self):
        return self._context.get("ocr", dict).get("offset", 10)

    def get_database(self):
        database = self._context.get('database', {})
        if 'mongodb' in database.keys() or 'sqlite' in database.keys():
            return 'mongodb' in database.keys() and 'mongodb' or 'sqlite'
        else:
            raise ValueError('database config error')

    def fetch(self, *args):
        """Fetch child collection from conf content.
        :arg list required args: field arguments
        :return dict/str/int/float/bool content or error
        """
        if not args:
            raise ValueError("Input arguments are empty")
        firstly = True
        collection = None
        for arg in args:
            if firstly:
                collection = self._context.get(arg)
                firstly = False
            else:
                collection = collection.get(arg)

        if not isinstance(collection, str) and \
                not isinstance(collection, dict) and \
                not isinstance(collection, int) and \
                not isinstance(collection, float) and \
                not isinstance(collection, bool) and \
                not isinstance(collection, list):
            raise ValueError("Fetch collection %s are not valid" % str(collection))
        return collection


def init_config(logname='autoserv.log'):
    conf = Configuration()
    log_file = os.path.join(conf.get_dirname().get('log'), logname)
    config_logging_environment(log_file)
    return conf