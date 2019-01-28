"""
File utilities
"""

import argparse
import glob
import os
import re
import shutil
import sys
from zipfile import ZipFile
from .display import print_docstring


def test_sources(sources):
    """
    Test whether source files are available.
    """
    for fil in sources:
        res = os.path.isfile(fil)
        if not res:
            print('\n', fil, "is missing! Please download from NHDv2\n")
            sys.exit(1)
        print(fil, os.path.isfile(fil))


def get_arguments(args):
    """
    Parse command line arguments. Not sure whether that is the correct place
    for that function in the long run.
    """
    parser = argparse.ArgumentParser()
    for item in args:
        parser.add_argument(
            item[0], item[1], action='store_true', help=item[2])
    return parser.parse_args()


def extend_from_snippets(snippets, directory, extension):
    return [os.path.join(directory, item + extension) for item in snippets]


def get_publish_snippets(directory):
    ret = []
    files = os.listdir(directory)
    for item in files:
        if re.search('.shp$', item):
            ret.append(item.replace('.shp', ''))
    ret.sort()
    return ret


def get_file_list(root, sources, snippet):
    """
    Expand a list of file patterns

    Args:
        root(str): Root directory
        sources(list(str)): Variable part of path pattern
        snippet(str): Fixed part of path pattern

    Returns:
        list(str): List of full paths
    """
    return [os.path.join(root, item, snippet) for item in sources]


@print_docstring
def ensure_directory(directory, empty=False):
    """
    Check whether directory exist, create if necessary
    """
    print(directory)
    if empty:
        shutil.rmtree(directory)
    try:
        os.makedirs(directory)
    except FileExistsError:
        if not os.path.isdir(directory):
            print('File exist but not a directory')
            sys.exit(1)


@print_docstring
def zip_shp(shp_name):
    """
    Zip shapefile for upload, creates shapefile.zip in same location
    as shapefile.shp
    """
    if not re.match('^.*.shp$', shp_name):
        print(shp_name, ': Incorrect file extension\n', sep='')
        sys.exit(1)
    snippet = shp_name[:-4]
    zipfile = '.'.join([snippet, 'zip'])
    files = glob.glob(snippet + '*')
    files = (item for item in files if not '.zip' in item)
    with ZipFile(zipfile, 'w') as zip:
        for fil in files:
            print(fil)
            zip.write(fil)
    print(zipfile, 'created')
    return zipfile
