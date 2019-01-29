"""
Bootstrap, ensure data sources
"""
# standard library
import os
import shutil
from zipfile import ZipFile
# third party
import requests
from tqdm import tqdm
# project
from .shapefile import gdb_to_shp
from .files import ensure_directory
from . import bootstrap


class CreationError(Exception):
    pass


def copy_tree(source_name, dest, **kwargs):
    dest = kwargs.get('directory') or dest
    shutil.copytree(source_name, dest)


def simple_download(url, dest, **kwargs):
    resp = requests.get(url, stream=True)
    with open(dest, 'wb') as handle:
        for data in tqdm(resp.iter_content(chunk_size=32000)):
            handle.write(data)


def unzip(zipf, dest, **kwargs):
    with ZipFile(zipf) as zf:
        zf.extractall(os.path.split(zipf)[0])


def check_or_create_files(
        source_path,
        file_path,
        directory='.',
        create_function=copy_tree,
        create_kwargs={}
    ):
    """
    Check whether a file exists, if not attempt creation by adding
    source to local data directory.
    """
    if isinstance(create_function, str):
        create_function=getattr(bootstrap, create_function)
    ensure_directory(directory)
    if not os.path.isfile(file_path):
        print(
            '\nAttempting creation of {}\nfrom {}\n'.format(
                file_path, source_path))
        create_function(source_path, file_path, **create_kwargs)
        if not os.path.isfile(file_path):
            raise CreationError('{} MISSING'.format(file_path))
    print('{} AVAILABLE'.format(file_path))