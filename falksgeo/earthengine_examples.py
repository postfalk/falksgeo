# pylint:disable=E0401
"""
Some example EE images for test downloading
"""
# standard library
from datetime import datetime, timedelta
# third party
import ee


def get_image():
    """
    Perform raster processing on Earthengine within this function and return
    an Earthengine image object containing the result.
    """
    ee.Initialize()
    print('\nCalculate image on EE')
    date_range = ['2000-01-01', '2020-01-01']
    ndvi_layer = (
        ee.ImageCollection('LANDSAT/LC8_L1T_8DAY_NDVI')
          .filterDate(*date_range).reduce(ee.Reducer.mean())).multiply(255)
    return ndvi_layer


def add_time(image):
    """
    Add a band containing time.
    """
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
