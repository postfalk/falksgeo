# pylint:disable=E0401
"""
Utilities for shapefile manipulation.
"""
import os
import re
from collections import OrderedDict
from copy import deepcopy
from csv import DictReader
from typing import Callable
from zipfile import ZipFile
import fiona
from shapely.geometry import Point, mapping
import geopandas
import pandas as pd
from .display import PercentDisplay, print_docstring
from .transformations import empty
from .files import ensure_directory
from .filters import empty_filter
from .pandas import concat_dataframes


def select_fields(dic:dict, fields:list[str]) -> dict:
    """
    Reduce the fields in a record accoring to a list of fieldnames (keys).

    Args:
        record(dict): A dictionary.
        files(list[str]): A list of fieldnames
    Returns:
        dict
    """
    new_dic = deepcopy(dic)
    if fields:
        props = new_dic.get('properties')
        for item in dic['properties']:
            if item not in fields:
                props.pop(item)
    return new_dic


def create_remap(attributes) -> Callable:
    """
    Create a mapping function from an attribute list and ensure compatible
    schema across input layers.

    Args:
        attributes(dict): A dictionary with keys.
    Returns:
        Callable
    """

    def remap(record:dict, schema:bool=False) -> dict:
        """
        An example renap function.

        Args:
            record(dict): A GeoJSON or a Fiona schema dict
            schema(bool): Flag indicating that a schema is remapped, only
                needed when new fields are created.
        Returns:
            dict
        """
        del schema
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
    filter_function=empty_filter, filter_kwargs=None,
    fields=None, layer=None, limit=None
):
    """
    Copy, remap, and filter a shapefile
    """
    filter_kwargs = filter_kwargs if filter_kwargs else {}
    print(f'{inputname} => {outputname}')
    with fiona.open(inputname, layer=layer) as collection:
        percentage = PercentDisplay(collection, limit=limit)
        schema = remap_function(collection.schema.copy(), schema=True)
        schema = select_fields(schema.copy(), fields)
        kwargs = {
            'mode': 'a' if append else 'w',
            'driver': 'ESRI Shapefile',
            'schema': schema,
            'crs': collection.crs}
        with fiona.open(outputname, **kwargs) as output:
            for item in collection:
                try:
                    percentage.inc()
                except StopIteration:
                    break
                # this is a little bit complicated but here for compatibility
                # with the old library design and the new immuable fiona objects
                geometry = item.geometry
                item = {'properties': dict(item.properties)}
                item = remap_function(item)
                item = select_fields(item, fields)
                new_item = fiona.Feature(
                    geometry=geometry,
                    properties=fiona.Properties.from_dict(
                        item.get('properties')))
                if filter_function(new_item, **filter_kwargs):
                    output.write(new_item)
        percentage.display()
    print(f'\n{outputname} generated\n')


def copy_shp(
    inputname, outputname, append=False, remap=None, remap_function=None,
    filter_function=None, fields=None, sort=None,
    reproject=None
):
    """
    Copy, remap, and filter a shapefile using GeoPandas
    """
    fields = fields if fields else []
    sort = sort if sort else []
    fields = fields.copy()
    print(f'{inputname} => {outputname}')
    df = geopandas.read_file(inputname)
    if append and os.path.isfile(outputname):
        edf = geopandas.read_file(outputname)
        df = pd.concat([df, edf], ignore_index=True)
    if remap:
        df = df.rename(columns=remap)
    if remap_function:
        # remap function might swallow crs
        crs = df.crs
        df = df.apply(remap_function, axis=1)
        df.set_crs(crs)
    if filter_function:
        df = df[df.apply(filter_function, axis=1, result_type='reduce')]
    if sort:
        df.sort_values(by=sort, inplace=True)
        df.reset_index(drop=True, inplace=True)
    if fields:
        if 'geometry' not in fields:
            fields.append('geometry')
        df = df[fields]
    if isinstance(reproject, int):
        reproject = f'epsg:{reproject}'
    if reproject:
        df = df.to_crs(reproject)
    df.to_file(outputname, driver='ESRI Shapefile')
    print(f'\n{outputname} generated\n')


@print_docstring
# This is too convoluted, TODO: slate for removal
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


def annotate(infile, annotation_files, outfile, index='comid', use=None):
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
    ensure_directory(os.path.split(dest_path)[0])
    with fiona.open(source_path, layer=layer) as collection:
        meta = collection.meta
        meta['driver'] = 'ESRI Shapefile'
        print(meta['schema'])
        # extract incompatible types from schema and convert to string
        incompatible = []
        fields = meta['schema']['properties']
        for item in fields:
            if fields[item] in ['datetime']:
                fields[item] = 'str:255'
                incompatible.append(item)
        # print(incompatible)
        with fiona.open(dest_path, 'w', **meta) as shp:
            for item in collection:
                for key in item:
                    if key in incompatible:
                        item[key] = str(item[key])
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
