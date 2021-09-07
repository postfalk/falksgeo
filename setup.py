"""
The module setup
"""
import subprocess
import sys
from setuptools import setup


def get_installed_gdal():
    """
    Read the available GDAL version from the system and install
    GDAL accordingly.

    Returns:
        str - the installed GDAL version as text or
        None - if no version is found
    """
    res = subprocess.run(
        ['gdalinfo', '--version'], capture_output=True, check=True)
    parts = res.stdout.decode('utf-8').split(' ')
    try:
        return parts[1].strip(',')
    except AttributeError:
        return None


gdal_version = get_installed_gdal()
if not gdal_version:
    print('Please, install GDAL on your system before proceeding.')
    sys.exit(1)


setup(
    name='falksgeo',
    version='0.1.3',
    description='Geoprocessing functions to be used in projects',
    url='https://github.com/postfalk/falksgeo',
    author='Falk Schuetzenmeister',
    author_email='falk_email@yahoo.com',
    license='BSD-2-clause',
    packages=['falksgeo'],
    zip_safe=False,
    install_requires=[
        'gdal=={}'.format(gdal_version),
        'numpy>=1.20',
        'pyproj>=3.0.1',
        'arcgis>=1.8',
        'geopandas>=0.9',
        'earthengine-api>=0.1.256:',
        'oauth2client>=4.1.3',
        'rasterio>=1.2',
        'requests>=2.25',
        'tqdm>=4.59',
        'nose'
    ]
)
