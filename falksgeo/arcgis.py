"""
Utils to interact with ArcGIS online
"""
import os
from getpass import getpass
import sys
import arcgis
from arcgis.features import FeatureLayerCollection
from falksgeo.display import print_docstring


# ensure these settings for safe publishing
DEFAULT_AGO_LAYER_CONFIG = {
    'capabilities': 'Query',
    'syncEnabled': False,
    'allowGeometryUpdates': False,
    'supportsAppend': False
}


def get_gis(portal, user, password=None):
    """
    Connect to GIS portal
    """
    if not password:
        password = getpass('Password for {}@{}: '.format(user, portal))
    try:
        gis = arcgis.gis.GIS(portal, user, password)
    except RuntimeError:
        print('\nCould not connect to GIS\n')
        sys.exit(1)
    print('\nConnected: {}\n'.format(gis))
    return gis


def exact_find(gis, name, typ):
    """
    The ArcGIS online search function picks up inexact matches. Double-check
    whether we are getting the right item
    """
    res = gis.content.search('title: {}'.format(name), typ)
    for item in res:
        if item.title == name:
            return item


@print_docstring
def publish(zipfile, gis, folder=None):
    """
    Push layer to ArcgisOnline
    """
    if folder:
        gis.content.create_folder(folder)
    name = os.path.split(zipfile)[1].replace('.zip', '')
    shapefile = exact_find(gis, name, 'Shapefile')
    if not shapefile:
        item_properties = {'title': name}
        shapefile = gis.content.add(
            item_properties, zipfile, folder=folder)
        print('Shapefile {} created'.format(shapefile))
        # Don't use overwrite argument, it behaves very funny
        service = shapefile.publish()
        print('Shapefile {} published'.format(shapefile))
    else:
        service = exact_find(gis, name, 'Feature Layer')
        print(service)
        layer = FeatureLayerCollection.fromitem(service)
        layer.manager.overwrite(zipfile)
        print('Feature Layer {} updated with {}'.format(service, shapefile))
    service.share(everyone=True)
    print('Service {} shared with everyone'.format(service))


def style_ago(gis, item, style, overwrites=DEFAULT_AGO_LAYER_CONFIG):
    """
    Style feature with name item
    """
    service = exact_find(gis, item, 'Feature ')
    print('\nStyle {}'.format(service))
    layer = FeatureLayerCollection.fromitem(service)
    layer.layers[0].manager.update_definition(style)
    # add standard definitions for a secure FeatureService
    # (disable editing)
    layer.manager.update_definition(overwrites)
