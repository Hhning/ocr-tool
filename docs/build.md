# build SigmaRIS

## requirements

- [NSIS](http://nsis.sourceforge.net/Main_Page) Make windows installation package
- [PyInstaller](http://www.pyinstaller.org/) Freeze python programs into stand-alone executables

## build
```shell
pyinstaller app.spec
makensis package.nsi    # make sure NSIS is in the PATH env, if not please use NSIS GUI compile package.nsi
```
After these operations, the installation package will be generated in dist dir.
