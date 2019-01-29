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
        'Fiona==1.8.4',
        'rasterio==1.0.15',
        'geopandas==0.4.0',
        'earthengine-api==0.1.164',
        'requests==2.21',
        'tqdm==4.30'
    ]
)
