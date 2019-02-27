"""
Bootstrap, hash, and ensure data sources
"""
# standard library
import os
import json
import hashlib
import shutil
from zipfile import ZipFile
# third party
import requests
from tqdm import tqdm
# project
# these imports make it possible to refer to them in
# configuration files by name without import
from .shapefile import gdb_to_shp, csv_to_shp
from .earthengine import raster_download
from .files import ensure_directory
from . import bootstrap


BLOCKSIZE = 65536


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


def hash_file(file_path):
    """
    Hash a file to track changes
    """
    # see https://www.pythoncentral.io/hashing-files-with-python/
    hasher = hashlib.md5()
    with open(file_path, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    return hasher.hexdigest()


def check_source_changes(
        sources, hash_store_name=None, no_hash_store_default=False,
        key_not_exist_default=False
    ):
    """
    Track upstream source changes.

    Args:
        sources: lst(str) - List of upstream sources (filenames)
        hash_store_name: str - Filename where to store hashes
        no_hash_store_default: boolean - Default return when no store present
        key_not_exist_default: boolean - Default return when no key present

    Returns:
        boolean: Whether upstream sources should be considered changed
    """
    ret = False
    hash_dic = {}
    hsh = ''
    if not hash_store_name:
        if no_hash_store_default:
            print('Not tracking sources: Overwrite')
        else:
            print('Not tracking changes: Assume no change')
        return bool(no_hash_store_default)
    try:
        with open(hash_store_name) as fil:
            hash_dic = json.loads(fil.read())
    except FileNotFoundError:
        pass
    if not isinstance(sources, (list, tuple)):
        sources = [sources]
    for item in sources:
        if not os.path.isfile(item):
            print('Source is not a file')
            continue
        try:
            hsh = hash_dic[item]
        except KeyError:
            hsh = None
            if key_not_exist_default:
                print('Key does not exist in hash file: Overwrite results')
                ret = True
            else:
                print('Key does not exist in hash file: Assume no change')
        new_hash = hash_file(item)
        if hsh:
            if hsh != new_hash:
                print('Upstream source changed')
                ret = True
            else:
                print('Upstream sources did not change')
        hash_dic.update({item: new_hash})
        hash_store_new = json.dumps(hash_dic)
        with open(hash_store_name, 'w') as fil:
            fil.write(hash_store_new)
    return ret


def check_file_exists(file_path):
    """
    Check whether file exists
    """
    return os.path.isfile(file_path)


def check_or_create_files(
        source_path, file_path, directory=None, create_function=copy_tree,
        create_kwargs={}, hash_store_name=None
    ):
    """
    Check whether a file exists, if not attempt creation by adding
    source to local data directory.
    """
    if isinstance(create_function, str):
        create_function=getattr(bootstrap, create_function)
    if directory:
        ensure_directory(directory)
    create = (
        not check_file_exists(file_path) or
        check_source_changes(file_path, hash_store_name=hash_store_name))
    if create:
        print(
            '\nAttempting creation of {}\nfrom {}\n'.format(
                file_path, source_path))
        create_function(source_path, file_path, **create_kwargs)
        if not os.path.isfile(file_path):
            raise CreationError('{} MISSING'.format(file_path))
    print('{} AVAILABLE'.format(file_path))


def get_from_tuple(tpl, idx):
    try:
        return tpl[idx]
    except IndexError:
        pass


def get_assets(list_of_assets, hash_store_name=None):
    """
    Try to download and install data sources for a project. Provide source
    that can handled by the function. The destination should be a file that
    is generated by the function. Extra_kwargs will be passed to the function.
    Some built-in functions can be called by name as string
    (e.g. 'simple_download', 'copy_tree', and 'unzip')

    Args:
        list_of_assets:
            list of tuples(
                source_str, dest_str, str or function, extra_kwargs)
    """
    try:
        for ds in list_of_assets:
            check_or_create_files(
                ds[0], ds[1], create_function=ds[2],
                create_kwargs=get_from_tuple(ds, 3),
                hash_store_name=hash_store_name)
    except CreationError:
        print('Dataset MISSING and creation FAILED\n')
