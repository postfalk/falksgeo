"""
Filter functions
"""
from functools import partial
import operator
import pyproj
import fiona
from shapely.geometry import shape
from shapely.ops import transform


def empty_filter(item, *args, **kwargs):
    """
    Placeholder function to pass along instead of filters
    """
    return True


def missing_filter(item, filterset=[]):
    if item['properties']['comid'] in filterset:
        return False
    if not item['properties']['ftype'] in ['StreamRiver', 'ArtificialPath']:
        return False
    return True


def final_filter(item):
    if item['properties']['ftype'] == 'Pipeline':
        return False
    if item['properties']['ftype'] == 'Coastline':
        return False
    return True


def build_filterset():
    """
    Build a list of comids in the dataset
    """
    with open(config.COMID_REFERENCE) as fil:
        return {int(line.strip()) for line in fil}


def filter_by_comid(record, filterset=[]):
    """
    Filter by comids in the project
    """
    return record['properties']['comid'] in filterset


def filter_by_record(
    record, attribute=None, value=None, compare='eq'):
    """
    Filter on data
    """
    compf = getattr(operator, compare)
    return compf(record['properties'][attribute], value)


def get_shape_filter(shapefile):
    """
    Return shapefile filter. All the geoprocessing is done only once for that
    reason we are using a generator function.
    """
    with fiona.open(shapefile) as collection:
        shp = collection[0]['geometry']
        project = partial(
            pyproj.transform,
            pyproj.Proj(init=collection.crs['init']),
            pyproj.Proj(init='epsg:4326'))
        shp = transform(project, shape(shp))

    def filter_function(item):
        if item['properties'].get('available'):
            return True
        return shp.intersects(shape(item['geometry']))

    return filter_function
