import os
from datetime import datetime
from functools import reduce
from itertools import product
import re
import shutil
from time import sleep
from zipfile import ZipFile
from affine import Affine
import ee
import fiona
import fiona.transform
import rasterio
import rasterio.merge
import requests
import shapely.geometry
from shapely.geometry import mapping, Polygon
from falksgeo.files import ensure_directory
from falksgeo.earthengine_examples import get_normalized_image


def download_image(options, tmp_image, image=get_normalized_image()):
    """
    Download the image from Google Earthengine
    """
    ee.Initialize()
    print('Download started')
    path = image.getDownloadUrl(options)
    print(path)
    resp = requests.get(path, stream=False)
    if resp.status_code != 200:
        print(resp.content)
    else:
        with open(tmp_image, 'wb') as handle:
            for chunk in resp.iter_content(chunk_size=128000):
                print('.', end='')
                handle.write(chunk)


def floatrange(start, stop, step):
    """
    Range function for float type, see:
    https://www.pythoncentral.io/pythons-range-function-explained/

    This is a little bit fuzzy due to imprecision with float data type
    """
    i = start
    while i < stop:
        yield i
        i += step


def get_tif_files(zipfile):
    return [
        item for item in zipfile.namelist()
        if re.match('^.*\.tif$', item)]


def generate_stitch_directory(path, step):
    directory = os.path.join(path, str(step).replace('.', '_'))
    ensure_directory(directory)
    return directory


def generate_filename(coords):
    return 'EE_{}_{}.tif'.format(
        str(coords[0][0]).replace('-', 'w')[0:8],
        str(coords[0][1]).replace('-', 's')[0:8])


def generate_path(path, coords, step):
    directory = generate_stitch_directory(path, step)
    name = generate_filename(coords)
    return os.path.join(directory, name)


def region_from_shape(shapefilename):
    """
    Returns bbox from shape in EE format
    """
    with fiona.open(shapefilename) as collection:
        bds = collection.bounds
        coords = [
            [bds[0], bds[1]], [bds[0], bds[3]],
            [bds[2], bds[3]], [bds[2], bds[1]]]
        box = {'type': 'Polygon', 'coordinates': [coords + [coords[0]]]}
        transformed = fiona.transform.transform_geom(
            collection.meta['crs']['init'], 'epsg:4326', box)
        return transformed['coordinates'][0][:-1]


def chunks_from_region(region, step=0.02):
    min_x = reduce(lambda a,b: a if a < b[0] else b[0], region, 180)
    min_y = reduce(lambda a,b: a if a < b[1] else b[1], region, 90)
    max_x = reduce(lambda a,b: a if a > b[0] else b[0], region, -180)
    max_y = reduce(lambda a,b: a if a > b[1] else b[1], region, -90)
    coords = product(
        floatrange(min_x, max_x, step), floatrange(min_y, max_y, step))
    ret = [
        [[crd[0], crd[1]], [crd[0] + step, crd[1]],
        [crd[0] + step, crd[1] + step], [crd[0], crd[1] + step]]
        for crd in coords]
    return ret


def chunk_filter(chunks, shapefilename, map_file_path=None):
    """
    Filter chunks by the first feature of a shapefile and
    store chunk map to disk if map_file_name is provided.
    """
    ret = []
    with fiona.open(shapefilename) as collection:
        crs = collection.meta['crs']['init']
        odd_geom = collection[0]['geometry']
        geom = fiona.transform.transform_geom(crs, 'epsg:4326', odd_geom)
    shape = shapely.geometry.shape(geom)
    for chunk in chunks:
        box = shapely.geometry.Polygon(chunk + [chunk[0]])
        if shape.intersects(box):
            ret.append(chunk)
    if map_file_path:
        chunks_to_shapefile(ret, map_file_path)
    return ret


def chunks_to_shapefile(chunks, shapefilename):
    """
    Include this here for convenience and coverage evaluation
    """
    schema = {'geometry': 'Polygon', 'properties': {'rasterfile': 'str'}}
    args = shapefilename, 'w', 'ESRI Shapefile', schema
    with fiona.collection(*args, crs='epsg:4326') as output:
        for item in chunks:
            output.write({
                'geometry': mapping(Polygon(item + [item[0]])),
                'properties': {
                    'rasterfile': generate_filename(item)}})


def get_chunks(shp, step=1, map_file_path=None):
    region = region_from_shape(shp)
    chunks = chunks_from_region(region, step=step)
    return chunk_filter(chunks, shp, map_file_path=map_file_path)


def download_parts(
        area, options, dest='/tmp/', step=1, image=get_normalized_image(),
        clean=False
    ):
    """
    Download raster in chunks Google Earth Engine can handle
    """
    ret = []
    ensure_directory(dest)
    tile_map = os.path.join(dest, 'downloaded_tiles_{}.shp'.format(step))
    tmp_zip = os.path.join(dest, 'tmp.zip')
    chunks = get_chunks(area, step, map_file_path=tile_map)
    print('{} chunks to process'.format(len(chunks)))
    for item in chunks:
        new_filename = generate_path(dest, item, step)
        ret.append(new_filename)
        options['region'] = str(item)
        if not os.path.isfile(new_filename) or clean:
            download_image(options, tmp_zip, image)
            with ZipFile(tmp_zip) as zipfile:
                tif = get_tif_files(zipfile)
                for item in tif:
                    filename = zipfile.extract(item, dest)
                    shutil.move(filename, new_filename)
        else:
            print('{} ok'.format(new_filename))
    return ret


def new_profile(files):
    """
    Determine new profile value from list of input files
    """
    profile = files[0].profile
    affine = [files[0].profile['transform'][item] for item in range(0, 6)]
    for fil in files:
        aff = fil.profile['transform']
        if aff[2] < affine[2]:
            affine[2] = aff[2]
        if aff[5] > affine[5]:
            affine[5] = aff[5]
    profile['transform'] = Affine(*affine)
    return profile


def merge(filelist, dest, nodata=-32768):
    files = [rasterio.open(fil) for fil in filelist]
    if files:
        profile = new_profile(files)
        newprofile = new_profile(files)
        new_raster = rasterio.merge.merge(files, nodata=nodata)
        profile['height'] = new_raster[0].shape[1]
        profile['width'] = new_raster[0].shape[2]
        profile['nodata'] = nodata
        with rasterio.open(dest, 'w', **profile) as dst:
            dst.write(new_raster[0])
    else:
        print('No images to process')


def image_to_cloud(
        options, image=get_normalized_image(),
        bucket=None, prefix=None, region=None):
    """
    Implements recommended way of storing downloads into GCS
    """
    # TODO: finalize
    # see https://github.com/google/earthengine-api/blob/master/python/ee/batch.py
    print('Send image to Google Cloud Storage')
    ee.Initialize()
    options.update({
        'bucket': options.get('bucket') or bucket or 'gde_data',
        'fileNamePrefix': options.get('fileNamePrefix') or prefix or 'pls_name'
        'region': options.get(region) or region})
    task = ee.batch.Export.image.toCloudStorage(image, **options)
    start = datetime.now()
    task.start()
    while task.status()['state'] not in {'COMPLETED', 'FAILED'}:
        print(datetime.now() - start, '\n', task.status(), '\n')
        sleep(2)
    else:
        print(task.status())


def raster_download(
        area_shape, dest_raster, dest='/tmp/', image_options={}, step=1,
        image=get_normalized_image
        ):
        files = download_parts(
            area_shape, image_options, step=step, clean=False,
            ee_function=ee_function, dest=dest)
        merge(files, dest_raster)
