"""
Utils for shapefile manipulation
"""

from collections import OrderedDict
from copy import deepcopy
import fiona
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


@print_docstring
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
def annotate_file(infile, annotationfile, outfile, index='comid'):
    df = geopandas.read_file(infile)
    df.set_index(index)
    df[index] = df[index].apply(int)
    attributes = pd.read_csv(annotationfile, index_col=0)
    ndf = df.merge(attributes, on=index, how='left')
    ndf.to_file(outfile, driver='ESRI Shapefile')
