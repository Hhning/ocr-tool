# SigmaRIS develop document

## Source Tree

```sh
│  .gitignore
│  app.json             # config file
│  app.py               # main file
│  app.spec             # pyinstaller config
│  get-ICAfile_v3.ps1   # deprecated file
│  package.nsi          # NSIS config
│  qt.conf              # Qt config
│  README.md            # README
│  requirements.txt     # python requirements
│  setup.py             # python setup
│
├─deps                  # project dependent libraries
│      keyboard-0.11.0-py2.py3-none-any.whl
│      sigma_sdk-1.0-py2.py3-none-any.whl
│
├─docs                  # project documents
│      build.md         # build document
│      dev.md           # develop document
│
└─sigmaris              # python package
    │  button.py
    │  capture.py
    │  config.py
    │  frame.py
    │  overlay.py
    │  request.py
    │  res_rc.py
    │  settings.py
    │  singleapplication.py
    │  task.py
    │  tray.py
    │  ui_frame.py
    │  utils.py
    │  __init__.py
    │
    └─res                   # Qt resource
        │  frame.ui         # UI
        │  res.qrc          # qrc
        │  style.qss        # stylesheet
        │
        ├─images            # pictures
        │      green.png
        │      logo.ico
        │      red.png
        │      tail.png
        │      tray.png
        │      yellow.png
        │
        └─translations      # i18n
                qt_zh_CN.qm
                zh_CN.qm
                zh_CN.ts
```

## install develop environment
- Python3.4
- PyQt5.5.1
- PyInstaller(If the installation fails, see [Unofficial Windows Binaries for Python Extension Packages](https://www.lfd.uci.edu/~gohlke/pythonlibs/))
- keyboard(in deps)
- sigma-sdk(in deps)
- NSIS

## run application
```sh
python app.py
```

## deploy application
1. compile UI files
2. update and release translations
3. compile qrc files
4. pyinstall app.spec
