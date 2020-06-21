# -*- mode: python -*-

block_cipher = None

from distutils.sysconfig import get_python_lib
from os import path
skimage_plugins = Tree(
    path.join(get_python_lib(), "skimage","io","_plugins"),
    prefix=path.join("skimage","io","_plugins"),
    )
scipy_extra = path.join(get_python_lib(), 'scipy', 'extra-dll')

a = Analysis(['autoserv.py'],
             pathex=['.', scipy_extra],
             binaries=[],
             datas=[('conf', 'conf'), ('ocr/engine/svm.sav', 'ocr/engine')],
             hiddenimports=['sklearn.neighbors.typedefs',
                            'scipy.fftpack._fftpack',
                            'scipy._lib.messagestream',
                            'pywt._extensions._cwt',
                            'skimage.io',
                            'skimage.io._plugins'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='autoserv',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               skimage_plugins,
               strip=False,
               upx=True,
               name='autoserv')
