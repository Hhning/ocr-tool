# SigmaOCR-Client

## requirements-dev

- Python3.4(for XP)
- PyQt5(GUI framework)
- keyboard(global hotkey)
- PyInstaller(build python)
- NSIS(make setup)

## i18n

pylupdate5.exe tray.py ui_frame.py overlay.py frame.py -ts res\translations\zh_CN.ts

## build

1. pyinstaller app.spec
2. makensis package.nsi