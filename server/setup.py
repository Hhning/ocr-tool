import glob
import os
import platform
import re
import shutil
import subprocess
import tarfile
import warnings

import click

OS = platform.system()
with open('ocr/__init__.py', 'rt') as f:
    VERSION = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)

def clean_docker():
    print('clean docker')
    if os.path.exists('deploy/docker/sigma-ocr'):
        shutil.rmtree('deploy/docker/sigma-ocr')


def clean_windows():
    print('clean windows')
    if os.path.exists('dist'):
        print('clean dist')
        shutil.rmtree('dist')
    if os.path.exists('build'):
        print('clean build')
        shutil.rmtree('build')
    if os.path.exists('deploy/windows/dist'):
        print('clean dist')
        shutil.rmtree('deploy/windows/dist')
    if os.path.exists('deploy/windows/build'):
        print('clean build')
        shutil.rmtree('deploy/windows/build')


def build_docker(version):
    clean_docker()
    print('build docker')
    os.makedirs('deploy/docker/sigma-ocr')
    shutil.copytree('conf', 'deploy/docker/sigma-ocr/conf', ignore=shutil.ignore_patterns('*.exe', '*.xml'))
    shutil.copytree('ocr', 'deploy/docker/sigma-ocr/ocr', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copyfile('autoserv.py', 'deploy/docker/sigma-ocr/autoserv.py')
    shutil.copyfile('requirements.txt', 'deploy/docker/sigma-ocr/requirements.txt')
    if OS != 'Linux':
        name = 'BuoyServer-{}'.format(version)
        warnings.warn('Only prepare files, please build docker on linux')
        with tarfile.open('deploy/{}.tar.gz'.format(name), 'w:gz') as tar:
            for root, _, files in os.walk('deploy/docker'):
                prefix = root.replace('deploy/docker', name)
                for file in files:
                    fullpath = os.path.join(root, file)
                    print(fullpath)
                    arcname = os.path.join(prefix, file)
                    tar.add(fullpath, arcname)
        return
    subprocess.call(['docker', 'build', '-t', 'sigmaocr:{}'.format(version), '.'], cwd='deploy/docker')


def build_windows(version):
    print('build windows')
    if OS != 'Windows':
        warnings.warn('Please build exe on windows')
        return
    subprocess.call(['pyinstaller', 'autoserv.spec', '-y'])
    subprocess.call(['makensis', '/DPRODUCT_VERSION={}'.format(version), 'deploy/windows/setup.nsi'])


def clean_all():
    clean_docker()
    clean_windows()


def build_all(version):
    build_docker(version)
    build_windows(version)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--platform', '-P', type=click.Choice(['windows', 'linux', 'all']), default='all')
def clean(platform):
    if platform == 'windows':
        clean_windows()
    elif platform == 'linux':
        clean_docker()
    else:
        clean_all()


@cli.command()
@click.option('--platform', '-P', type=click.Choice(['windows', 'linux', 'all']), default='all')
def make(platform):
    if platform == 'windows':
        build_windows(VERSION)
    elif platform == 'linux':
        build_docker(VERSION)
    else:
        build_all(VERSION)


@cli.command()
@click.option('--platform', '-P', type=click.Choice(['windows', 'linux', 'all']), default='all')
def make_clean(platform):
    if platform == 'windows':
        clean_windows()
        build_windows(VERSION)
        clean_windows()
    elif platform == 'linux':
        clean_docker()
        build_docker(VERSION)
        clean_docker()
    else:
        clean_all()
        build_all(VERSION)
        clean_all()


if __name__ == '__main__':
    cli()
