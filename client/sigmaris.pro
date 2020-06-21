TEMPLATE = app
TARGET = SigmaRIS
SOURCES = app.py
SOURCES += sigmaris/__init__.py
SOURCES += sigmaris/_logger.py
SOURCES += sigmaris/bbox.py
SOURCES += sigmaris/button.py
SOURCES += sigmaris/capture.py
SOURCES += sigmaris/config.py
SOURCES += sigmaris/constants.py
SOURCES += sigmaris/effect.py
SOURCES += sigmaris/enlarge.py
SOURCES += sigmaris/frame.py
SOURCES += sigmaris/image.py
SOURCES += sigmaris/launch.py
SOURCES += sigmaris/magnifier.py
SOURCES += sigmaris/menu.py
SOURCES += sigmaris/overlay.py
SOURCES += sigmaris/query.py
SOURCES += sigmaris/settings.py
SOURCES += sigmaris/task.py
SOURCES += sigmaris/tips.py
SOURCES += sigmaris/utils.py
SOURCES += sigmaris/web.py
FORMS = sigmaris/res/frame.ui
FORMS += sigmaris/res/bbox.ui
FORMS += sigmaris/res/settings.ui
RESOURCES = sigmaris/res/res.qrc
TRANSLATIONS = sigmaris/res/translations/zh_CN.ts

# update translations
# pylupdate5 sigmaris.pro