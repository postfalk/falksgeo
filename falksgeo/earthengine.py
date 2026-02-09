# pylint:disable=E0401
import os
from datetime import datetime
from functools import reduce
from itertools import product
import re
import shutil
from time import sleep
from typing import Any, Generator, Optional
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


def download_image(options: dict, tmp_image: str, image: Optional[Any] = None, project: Optional[str] = None) -> None:
    """
    Download the image from Google Earthengine
    """
    ee.Initialize(project=project)
    if os.path.isfile(tmp_image):
        print(f'{tmp_image} exist. Download skipped.')
        return
    image = get_normalized_image() if image is None else image
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


def floatrange(start: float, stop: float, step: float) -> Generator[float, None, None]:
    """
    Range function for float type, see:
    https://www.pythoncentral.io/pythons-range-function-explained/

    This is a little bit fuzzy due to imprecision with float data type
    """
    i = start
    while i < stop:
        yield i
        i += step


def get_tif_files(zipfile: ZipFile) -> list[str]:
    return [
        item for item in zipfile.namelist()
        if re.match('^.*\.tif$', item)]


def generate_stitch_directory(path: str, step: float) -> str:
    directory = os.path.join(path, str(step).replace('.', '_'))
    ensure_directory(directory)
    return directory


def generate_filename(coords: list) -> str:
    return 'EE_{}_{}.tif'.format(
        str(coords[0][0]).replace('-', 'w')[0:8],
        str(coords[0][1]).replace('-', 's')[0:8])


def generate_path(path: str, coords: list, step: float) -> str:
    directory = generate_stitch_directory(path, step)
    name = generate_filename(coords)
    return os.path.join(directory, name)


def region_from_shape(shapefilename: str) -> list:
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


def chunks_from_region(region: list, step: float = 0.02) -> list:
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


def chunk_filter(chunks: list, shapefilename: str, map_file_path: Optional[str] = None) -> list:
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


def chunks_to_shapefile(chunks: list, shapefilename: str) -> None:
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


def get_chunks(shp: str, step: int = 1, map_file_path: Optional[str] = None) -> list:
    region = region_from_shape(shp)
    chunks = chunks_from_region(region, step=step)
    return chunk_filter(chunks, shp, map_file_path=map_file_path)


def download_parts(
    area: str, options: dict, dest: str = '/tmp/', step: int = 1, image: Optional[Any] = None, clean: bool = False
) -> list:
    """
    Download raster in chunks Google Earth Engine can handle
    """
    image = get_normalized_image() if image is None else image
    ret = []
    ensure_directory(dest)
    tile_map = os.path.join(dest, f'downloaded_tiles_{step}.shp')
    tmp_zip = os.path.join(dest, 'tmp.zip')
    chunks = get_chunks(area, step, map_file_path=tile_map)
    print(f'{len(chunks)} chunks to process')
    for item in chunks:
        new_filename = generate_path(dest, item, step)
        ret.append(new_filename)
        options['region'] = str(item)
        if not os.path.isfile(new_filename) or clean:
            download_image(options, tmp_zip, image)
            with ZipFile(tmp_zip) as zipfile:
                tif = get_tif_files(zipfile)
                for tif_file in tif:
                    filename = zipfile.extract(tif_file, dest)
                    shutil.move(filename, new_filename)
        else:
            print(f'{new_filename} ok')
    return ret


def new_profile(files: list) -> dict:
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


def merge(filelist: list, dest: str, nodata: int = -32768) -> None:
    files = [rasterio.open(fil) for fil in filelist]
    if files:
        profile = new_profile(files)
        new_raster = rasterio.merge.merge(files, nodata=nodata)
        profile['height'] = new_raster[0].shape[1]
        profile['width'] = new_raster[0].shape[2]
        profile['nodata'] = nodata
        profile.update({
            'tiled': True,
            'compress': 'DEFLATE'
        })
        with rasterio.open(dest, 'w', **profile) as dst:
            dst.write(new_raster[0])
    else:
        print('No images to process')


def image_to_cloud(options: dict, image: Optional[Any] = None, bucket: Optional[str] = None, prefix: Optional[str] = None, region: Optional[Any] = None) -> None:
    """
    Implements recommended way of storing downloads into GCS
    """
    image = get_normalized_image() if image is None else image
    # TODO: finalize
    # see https://github.com/google/earthengine-api/blob/master/python/ee/batch.py
    print('Send image to Google Cloud Storage')
    print(options)
    options.update({
        'bucket': options.get('bucket') or bucket or 'gde_data',
        'fileNamePrefix': options.get('fileNamePrefix') or prefix or 'pls_name',
        'region': options.get('region') or region})
    ee.Initialize()
    task = ee.batch.Export.image.toCloudStorage(image, **options)
    start = datetime.now()
    task.start()
    while task.status()['state'] not in {'COMPLETED', 'FAILED'}:
        print(datetime.now() - start, '\n', task.status(), '\n')
        sleep(2)
    print(task.status())


def raster_download(
    area_shape: str, dest_raster: str, dest: str = '/tmp/', image_options: Optional[dict] = None, step: int = 1,
    image: Optional[Any] = None
) -> None:
    if image_options is None:
        image_options = {}
    image = get_normalized_image() if image is None else image
    files = download_parts(
        area_shape, image_options, step=step, clean=False,
        image=image, dest=dest)
    merge(files, dest_raster)
