from setuptools import setup


setup(
    name='falksgeo',
    version='0.1',
    description='Geoprocessing functions to be used in projects',
    url='https://github.com/postfalk/falksgeo',
    author='Falk Schuetzenmeister',
    author_email='falk_email@yahoo.com',
    license='BSD-2-clause',
    packages=['falksgeo'],
    zip_safe=False,
    install_requires=[
        'pyproj==1.9.6',
        'arcgis==1.5.2.post1',
        'geopandas==0.4.0',
        'earthengine-api==0.1.164',
        'oauth2client==4.1.3',
        'rasterio==1.0.15',
        'requests==2.21',
        'tqdm==4.30']
)
