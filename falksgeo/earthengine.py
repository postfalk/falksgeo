from datetime import datetime, timedelta
from time import sleep
import ee
import requests
import config


def get_image():
    """
    Perform raster processing on Earthengine within this function and return
    an Earthengine image object containing the result
    """
    ee.Initialize()
    print('\nCalculate image on EE')
    date_range = ['2000-01-01', '2020-01-01']
    ndvi_layer = (
        ee.ImageCollection('LANDSAT/LC8_L1T_8DAY_NDVI')
          .filterDate(*date_range).reduce(ee.Reducer.mean())).multiply(255)
    return ndvi_layer


def add_time(image):
    return image.addBands(
        image.metadata('system:time_start')
            .divide(1000 * 60 * 60 * 24))


def get_slope_image():
    ee.Initialize()
    now = datetime.now()
    ten_years_ago = now - timedelta(days=3652)
    collection1 = ee.ImageCollection(
        'LANDSAT/LC8_L1T_8DAY_NDVI').filterDate(
        ee.Date(ten_years_ago), ee.Date(now))
    collection2 = ee.ImageCollection(
        'LANDSAT/LT5_L1T_8DAY_NDVI').filterDate(
        ee.Date(ten_years_ago), ee.Date(now))
    merged = collection2.merge(collection1).map(add_time)
    return merged.select(
        ['system:time_start', 'NDVI']).reduce(
        ee.Reducer.linearFit()).select('scale').float()


def get_8bit_image():
    image = get_slope_image()
    return image.expression(
        '(scale * 100000) + 100', {'scale': image.select('scale')}).uint8()


def get_normalized_image():
    """
    Normalize change metrics in a way that it reflects average NDVI
    (int<10000) change within 10 years. Return as signed 16 bit integer.
    """
    image = get_slope_image()
    return image.expression(
        'scale * 3652 * 10000', {'scale': image.select('scale')}).toInt16()


def get_percentage_image():
    ee.Initialize()
    now = datetime.now()
    ten_years_ago = now - timedelta(days=3652)
    collection1 = ee.ImageCollection(
        'LANDSAT/LC8_L1T_8DAY_NDVI').filterDate(
        ee.Date(ten_years_ago), ee.Date(now))
    collection2 = ee.ImageCollection(
        'LANDSAT/LT5_L1T_8DAY_NDVI').filterDate(
        ee.Date(ten_years_ago), ee.Date(now))
    merged = collection2.merge(collection1).map(add_time)
    linear = merged.select(
        ['system:time_start', 'NDVI']).reduce(ee.Reducer.linearFit())
    return linear.expression(
        '((scale*now)+offset)/((scale*ten_years_ago)+offset)*100', {
            'scale': linear.select('scale'),
            'ten_years_ago': ten_years_ago.timestamp()/60/60/24,
            'now': now.timestamp()/60/60/24,
            'offset': linear.select('offset')}).uint8()


def download_image(options, image=get_slope_image()):
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
        with open(config.EE_RASTER_TMP_ZIP, 'wb') as handle:
            for chunk in resp.iter_content(chunk_size=128000):
                print('.', end='')
                handle.write(chunk)


def image_to_cloud(options, image=get_slope_image()):
    """
    Implements recommended way of storing downloads into GCS
    """
    # see https://github.com/google/earthengine-api/blob/master/python/ee/batch.py
    print('Send image to Google Cloud Storage')
    ee.Initialize()
    options.update({
        'description': 'ndviTrend',
        'bucket': 'gde_data',
        'fileNamePrefix': 'ndviTrend'})
    task = ee.batch.Export.image.toCloudStorage(image, **options)
    start = datetime.now()
    task.start()
    while task.status()['state'] not in {'COMPLETED', 'FAILED'}:
        print(datetime.now() - start, '\n', task.status(), '\n')
        sleep(2)
    else:
        print(task.status())
