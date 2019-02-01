"""
Utils for shapefile manipulation
"""
import os
import re
from collections import OrderedDict
from copy import deepcopy
from csv import DictReader
from zipfile import ZipFile
import fiona
from shapely.geometry import Point, mapping
import geopandas
import pandas as pd
from .display import PercentDisplay, print_docstring
from .transformations import empty
from .filters import empty_filter
from .pandas import concat_dataframes


def select_fields(record, fields):
    new_record = deepcopy(record)
    if fields:
        props = new_record.get('properties')
        for item in record['properties']:
            if item not in fields:
                props.pop(item)
    return new_record


def create_remap(attributes):
    """
    Create a mapping function from an attribute list and ensure compatible
    schema across input layers.
    """

    def remap(record):
        new_record = OrderedDict([
            ('geometry', record['geometry']), ('properties', OrderedDict())])
        for item in record['properties']:
            newkey = item.lower()
            if newkey in attributes:
                new_record['properties'][newkey] = record['properties'][item]
        return new_record

    return remap


@print_docstring
def copy_layer(
        inputname, outputname, append=False, remap_function=empty,
        filter_function=empty_filter, filter_kwargs={},
        fields=None, layer=None, limit=None
):
    """
    Copy, remap, and filter a shapefile
    """
    print(inputname, '=>', outputname)
    with fiona.open(inputname, layer=layer) as collection:
        percentage = PercentDisplay(collection, limit=limit)
        schema = remap_function(collection.schema.copy())
        schema = select_fields(schema.copy(), fields)
        write_mode = 'a' if append else 'w'
        args = write_mode, 'ESRI Shapefile', schema
        with fiona.open(outputname, *args, crs=collection.crs) as output:
            for item in collection:
                try:
                    percentage.inc()
                except StopIteration:
                    break
                item = remap_function(item)
                item = select_fields(item, fields)
                if filter_function(item, **filter_kwargs):
                    output.write(item)
        percentage.display()
    print('\n{} generated\n'.format(outputname))


@print_docstring
def create_variable(
    inputname, outputname, ref, variable='available', value=1, default=None,
    index='comid'):
    """
    Add a new variable to the dataset by partitioning a lookup table
    """
    prt = 500
    reference = [[] for i in range(0, prt)]
    for item in ref:
        batch = item % prt
        reference[batch].append(item)
    with fiona.open(inputname) as collection:
        percent = PercentDisplay(collection)
        schema = collection.schema.copy()
        schema['properties'][variable] = 'int:1'
        args = 'w', 'ESRI Shapefile', schema
        with fiona.open(outputname, *args, crs=collection.crs) as out:
            for item in collection:
                percent.inc()
                new_item = item.copy()
                props = new_item['properties']
                try:
                    batch = props[index] % prt
                    reference[batch].remove(props[index])
                    props[variable] = value
                except ValueError:
                    if default is not None:
                        props[variable] = default
                out.write(new_item)


@print_docstring
def merge_layers(input_layers, outputfile, remap=empty, debug=False):
    """
    Merge layers into a single layer
    """
    for index, layer in enumerate(input_layers):
        append = True if index else False
        kwargs = {'append': append, 'remap_function': remap}
        copy_layer(layer, outputfile, **kwargs, debug=debug)

# TODO: review
def annotate(infile, annotation_files, outfile, index='comid', use=[]):
    """
    Annotate additional properties using GeoPandas
    """
    df = geopandas.read_file(infile)
    df.set_index(index)
    attributes = concat_dataframes(annotation_files)
    if use:
        attributes = attributes[use]
    ndf = df.merge(attributes, on=index, how='left')
    ndf.to_file(outfile, driver='ESRI Shapefile')


@print_docstring
def annotate_file(infiles, outfile, index='comid'):
    """
    Annotate attributes from one file by another using index
    """
    infile = infiles[0]
    annotationfile = infiles[1]
    df = geopandas.read_file(infile)
    df.set_index(index)
    df[index] = df[index].apply(int)
    attributes = pd.read_csv(annotationfile, index_col=0)
    ndf = df.merge(attributes, on=index, how='left')
    ndf.to_file(outfile, driver='ESRI Shapefile')


@print_docstring
def gdb_to_shp(source_path, dest_path, layer=None):
    """
    Extract Shapefile from GDB
    """
    if not layer:
        return
    ensure_directories(os.path.split(dest_path)[0])
    with fiona.open(source_path, layer=layer) as collection:
        meta = collection.meta
        meta['driver'] = 'ESRI Shapefile'
        with fiona.open(dest_path, 'w', **meta) as shp:
            for item in collection:
                shp.write(item)


def csv_to_shp(
    source_path, dest_path, x_field='x', y_field='y', crs='epsg:4326'
):
    """
    Convert a point csv with x and y coordinates into a shapefile
    """
    print('Converting {} into a shapefile'.format(source_path))
    with open(source_path) as src:
        reader = DictReader(src)
        property_names = reader.fieldnames.copy()
        [property_names.remove(item) for item in [x_field, y_field]]
        schema = {
            'geometry': 'Point',
            'properties': {item:'str' for item in property_names}}
        meta = {'driver': 'ESRI Shapefile', 'crs': crs, 'schema': schema}
        with fiona.open(dest_path, 'w', **meta) as shp:
            for item in reader:
                geometry = mapping(
                    Point(float(item.pop(x_field)),
                          float(item.pop(y_field))))
                shp.write({
                    'geometry': geometry,
                    'properties': item})


@print_docstring
def zip_shp(shp_name):
    """
    Zip shapefile including all components.
    """
    if not re.match('^.*.shp$', shp_name):
        raise ValueError('{}: Incorrect file extension'.format(shp_name))
    if not os.path.isfile(shp_name):
        raise FileNotFoundError
    snippet = shp_name[:-4]
    zipfilename = '.'.join([snippet, 'zip'])
    with ZipFile(zipfilename, 'w') as zipf:
        for item in ['shp', 'shx', 'proj', 'dbf', 'prj', 'shp.xml']:
            fn = '.'.join([snippet, item])
            if os.path.isfile(fn):
                zipf.write(fn, os.path.basename(fn))
    return zipfilename
