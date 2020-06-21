import os
import re
import shutil
import subprocess


NSIS_PATH = r'C:\Program Files (x86)\NSIS'
os.putenv('PATH', '{};{}'.format(os.environ['PATH'], NSIS_PATH))

def clean():
    if os.path.exists('dist'):
        print('clean dist')
        shutil.rmtree('dist')
    if os.path.exists('build'):
        print('clean build')
        shutil.rmtree('build')

def build():
    print('PyInstaller')
    subprocess.call(['pyinstaller', 'app.spec'])
    print('MakeNSIS')
    with open('sigmaris/__init__.py', 'rt') as f:
        version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)
    subprocess.call(['makensis', '/DPRODUCT_VERSION={}'.format(version), 'setup.nsi'])


if __name__ == '__main__':
    clean()
    build()
